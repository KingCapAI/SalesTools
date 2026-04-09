"""Store address management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.address import Address
from ..models.store_user import StoreUser
from ..utils.store_dependencies import require_store_auth

router = APIRouter(prefix="/store/addresses", tags=["Store Addresses"])


class AddressCreate(BaseModel):
    label: Optional[str] = None
    first_name: str
    last_name: str
    company: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    phone: Optional[str] = None
    is_default: bool = False


class AddressUpdate(AddressCreate):
    pass


class AddressResponse(BaseModel):
    id: str
    label: Optional[str] = None
    first_name: str
    last_name: str
    company: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[AddressResponse])
async def list_addresses(
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """List all addresses for the current user."""
    return (
        db.query(Address)
        .filter(Address.store_user_id == user.id)
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .all()
    )


@router.post("/", response_model=AddressResponse, status_code=201)
async def create_address(
    data: AddressCreate,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Create a new address."""
    # If this is set as default, unset other defaults
    if data.is_default:
        db.query(Address).filter(
            Address.store_user_id == user.id,
            Address.is_default == True,
        ).update({"is_default": False})

    address = Address(
        store_user_id=user.id,
        **data.model_dump(),
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: str,
    data: AddressUpdate,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Update an existing address."""
    address = (
        db.query(Address)
        .filter(Address.id == address_id, Address.store_user_id == user.id)
        .first()
    )
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # If setting as default, unset other defaults
    if data.is_default:
        db.query(Address).filter(
            Address.store_user_id == user.id,
            Address.id != address_id,
            Address.is_default == True,
        ).update({"is_default": False})

    for field, value in data.model_dump().items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)
    return address


@router.delete("/{address_id}", status_code=204)
async def delete_address(
    address_id: str,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Delete an address."""
    address = (
        db.query(Address)
        .filter(Address.id == address_id, Address.store_user_id == user.id)
        .first()
    )
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    db.delete(address)
    db.commit()


@router.post("/{address_id}/default", response_model=AddressResponse)
async def set_default_address(
    address_id: str,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Set an address as the default."""
    address = (
        db.query(Address)
        .filter(Address.id == address_id, Address.store_user_id == user.id)
        .first()
    )
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Unset all defaults
    db.query(Address).filter(
        Address.store_user_id == user.id,
        Address.is_default == True,
    ).update({"is_default": False})

    address.is_default = True
    db.commit()
    db.refresh(address)
    return address
