"""Shipping logistics AI agent routes — analysis, recommendations, rate config."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.shipping import ShipmentAnalysis, ShipmentBatch, ShippingRate
from ..services import shipping_agent_service, bc_service
from ..utils.store_dependencies import require_store_role

router = APIRouter(prefix="/admin/shipping", tags=["Shipping Agent"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ShippingRateResponse(BaseModel):
    id: str
    method: str
    label: str
    origin: str
    destination: str
    cost_per_unit: int
    unit_type: str
    min_volume_cbm: Optional[float] = None
    max_volume_cbm: Optional[float] = None
    min_weight_kg: Optional[float] = None
    max_weight_kg: Optional[float] = None
    transit_days_min: int
    transit_days_max: int
    buffer_days: int
    is_active: bool
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ShippingRateCreate(BaseModel):
    method: str
    label: str
    origin: str = "Chittagong, BD"
    destination: str = "Los Angeles, US"
    cost_per_unit: int
    unit_type: str
    min_volume_cbm: Optional[float] = None
    max_volume_cbm: Optional[float] = None
    min_weight_kg: Optional[float] = None
    max_weight_kg: Optional[float] = None
    transit_days_min: int
    transit_days_max: int
    buffer_days: int = 5
    notes: Optional[str] = None


class ShippingRateUpdate(BaseModel):
    label: Optional[str] = None
    cost_per_unit: Optional[int] = None
    transit_days_min: Optional[int] = None
    transit_days_max: Optional[int] = None
    buffer_days: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class BatchResponse(BaseModel):
    id: str
    batch_number: int
    batch_label: Optional[str] = None
    recommended_method: str
    total_volume_cbm: float
    total_weight_kg: float
    estimated_shipping_cost: int
    cost_per_unit_avg: Optional[int] = None
    recommended_ship_date: Optional[datetime] = None
    estimated_arrival_date: Optional[datetime] = None
    latest_delivery_deadline: Optional[datetime] = None
    bc_order_numbers: Optional[str] = None
    order_count: int
    reasoning: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: str
    triggered_by: Optional[str] = None
    analysis_type: str
    status: str
    total_orders_analyzed: Optional[int] = None
    total_volume_cbm: Optional[float] = None
    total_weight_kg: Optional[float] = None
    estimated_savings_cents: Optional[int] = None
    recommendation_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    batches: list[BatchResponse] = []

    class Config:
        from_attributes = True


class TriggerAnalysisRequest(BaseModel):
    analysis_type: str = "full"
    use_mock: bool = False


class BatchStatusUpdate(BaseModel):
    status: str  # accepted, rejected


class PendingOrderResponse(BaseModel):
    bc_order_id: Optional[str] = None
    bc_order_number: str
    customer_name: str
    customer_number: Optional[str] = None
    order_date: Optional[str] = None
    requested_delivery_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: str = "USD"
    total_quantity: int
    estimated_volume_cbm: float
    estimated_weight_kg: float
    line_items: list[dict] = []


# ---------------------------------------------------------------------------
# Rate CRUD
# ---------------------------------------------------------------------------

@router.get("/rates", response_model=list[ShippingRateResponse])
async def list_rates(
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    return db.query(ShippingRate).order_by(ShippingRate.method).all()


@router.post("/rates", response_model=ShippingRateResponse, status_code=201)
async def create_rate(
    data: ShippingRateCreate,
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    rate = ShippingRate(**data.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.put("/rates/{rate_id}", response_model=ShippingRateResponse)
async def update_rate(
    rate_id: str,
    data: ShippingRateUpdate,
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    rate = db.query(ShippingRate).filter(ShippingRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Shipping rate not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)
    rate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/rates/{rate_id}")
async def delete_rate(
    rate_id: str,
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    rate = db.query(ShippingRate).filter(ShippingRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Shipping rate not found")
    db.delete(rate)
    db.commit()
    return {"detail": "Deleted"}


# ---------------------------------------------------------------------------
# Business Central Orders
# ---------------------------------------------------------------------------

@router.get("/bc-orders", response_model=list[PendingOrderResponse])
async def list_pending_bc_orders(
    mock: bool = Query(default=False, description="Use mock data"),
    _=Depends(require_store_role("admin")),
):
    from ..config import get_settings
    settings = get_settings()

    if mock or not settings.bc_client_id:
        orders = bc_service.generate_mock_orders()
    else:
        orders = await bc_service.get_pending_overseas_orders()
    return orders


# ---------------------------------------------------------------------------
# AI Analysis
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalysisResponse)
async def trigger_analysis(
    data: TriggerAnalysisRequest,
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    from ..config import get_settings
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env",
        )

    use_mock = data.use_mock or not settings.bc_client_id
    analysis = await shipping_agent_service.run_analysis(
        db=db,
        triggered_by="admin",
        analysis_type=data.analysis_type,
        use_mock=use_mock,
    )

    # Reload with batches
    db.refresh(analysis)
    return analysis


@router.get("/analyses", response_model=list[AnalysisResponse])
async def list_analyses(
    limit: int = Query(default=10, le=50),
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    analyses = (
        db.query(ShipmentAnalysis)
        .options(joinedload(ShipmentAnalysis.batches))
        .order_by(ShipmentAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )
    return analyses


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(ShipmentAnalysis)
        .options(joinedload(ShipmentAnalysis.batches))
        .filter(ShipmentAnalysis.id == analysis_id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


# ---------------------------------------------------------------------------
# Batch Management
# ---------------------------------------------------------------------------

@router.put("/batches/{batch_id}/status", response_model=BatchResponse)
async def update_batch_status(
    batch_id: str,
    data: BatchStatusUpdate,
    _=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    if data.status not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'accepted' or 'rejected'")

    batch = db.query(ShipmentBatch).filter(ShipmentBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch.status = data.status
    batch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch
