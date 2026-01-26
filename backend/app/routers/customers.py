"""Customer management routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer
from ..schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerList
from ..utils.dependencies import require_auth, get_current_user

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=List[CustomerList])
async def list_customers(
    search: Optional[str] = Query(None, description="Search by name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all customers with optional search."""
    query = db.query(Customer)

    if search:
        query = query.filter(Customer.name.ilike(f"%{search}%"))

    customers = query.order_by(Customer.name).offset(skip).limit(limit).all()
    return customers


@router.post("", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Create a new customer."""
    customer = Customer(
        name=customer_data.name,
        brand_name=customer_data.brand_name,
        website=customer_data.website,
        created_by_id=user.id,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get a customer by ID."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Update a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if customer_data.name is not None:
        customer.name = customer_data.name
    if customer_data.brand_name is not None:
        customer.brand_name = customer_data.brand_name
    if customer_data.website is not None:
        customer.website = customer_data.website

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Delete a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted successfully"}
