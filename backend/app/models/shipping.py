"""Shipping logistics models for overseas order batching and analysis."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class ShippingRate(Base):
    """Configurable shipping rates for overseas logistics."""
    __tablename__ = "shipping_rates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Method: ocean_fcl, ocean_lcl, air_freight
    method = Column(String(50), nullable=False, index=True)
    label = Column(String(255), nullable=False)

    # Route
    origin = Column(String(100), nullable=False, default="Chittagong, BD")
    destination = Column(String(100), nullable=False, default="Los Angeles, US")

    # Cost (cents). FCL: per container. LCL: per CBM. Air: per kg.
    cost_per_unit = Column(Integer, nullable=False)
    unit_type = Column(String(50), nullable=False)  # container, cbm, kg

    # Volume / weight constraints
    min_volume_cbm = Column(Float, nullable=True)
    max_volume_cbm = Column(Float, nullable=True)
    min_weight_kg = Column(Float, nullable=True)
    max_weight_kg = Column(Float, nullable=True)

    # Transit time
    transit_days_min = Column(Integer, nullable=False)
    transit_days_max = Column(Integer, nullable=False)
    buffer_days = Column(Integer, nullable=False, default=5)

    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShipmentAnalysis(Base):
    """Record of a shipping logistics AI analysis run."""
    __tablename__ = "shipment_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    triggered_by = Column(String(255), nullable=True)

    # full, quick
    analysis_type = Column(String(50), nullable=False, default="full")

    # pending, running, completed, failed
    status = Column(String(50), nullable=False, default="pending", index=True)

    # Input summary (JSON)
    input_summary = Column(Text, nullable=True)

    # AI output
    raw_ai_response = Column(Text, nullable=True)
    recommendation_summary = Column(Text, nullable=True)

    # Aggregates
    total_orders_analyzed = Column(Integer, nullable=True)
    total_volume_cbm = Column(Float, nullable=True)
    total_weight_kg = Column(Float, nullable=True)
    estimated_savings_cents = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batches = relationship(
        "ShipmentBatch",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="ShipmentBatch.batch_number",
    )


class ShipmentBatch(Base):
    """A recommended shipment batch grouping orders together."""
    __tablename__ = "shipment_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(
        String(36),
        ForeignKey("shipment_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    batch_number = Column(Integer, nullable=False)
    batch_label = Column(String(255), nullable=True)

    # ocean_fcl, ocean_lcl, air_freight
    recommended_method = Column(String(50), nullable=False)

    total_volume_cbm = Column(Float, nullable=False, default=0)
    total_weight_kg = Column(Float, nullable=False, default=0)

    # Costs in cents
    estimated_shipping_cost = Column(Integer, nullable=False, default=0)
    cost_per_unit_avg = Column(Integer, nullable=True)

    # Timeline
    recommended_ship_date = Column(DateTime, nullable=True)
    estimated_arrival_date = Column(DateTime, nullable=True)
    latest_delivery_deadline = Column(DateTime, nullable=True)

    # BC order references (JSON array of order numbers)
    bc_order_numbers = Column(Text, nullable=True)
    order_count = Column(Integer, nullable=False, default=0)

    reasoning = Column(Text, nullable=True)

    # proposed, accepted, rejected, shipped
    status = Column(String(50), nullable=False, default="proposed")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analysis = relationship("ShipmentAnalysis", back_populates="batches")
