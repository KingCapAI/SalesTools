"""Store shopping cart routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
import uuid

from ..database import get_db
from ..models.store_cart import CartItem
from ..models.store_product import Product, ProductVariant
from ..models.store_user import StoreUser
from ..utils.store_dependencies import get_current_store_user

router = APIRouter(prefix="/store/cart", tags=["Store Cart"])


class AddToCartRequest(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = 1
    customization: Optional[str] = None  # JSON string


class UpdateCartItemRequest(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: int
    unit_price: int
    customization: Optional[str] = None
    product_name: Optional[str] = None
    product_slug: Optional[str] = None
    product_image: Optional[str] = None
    variant_sku: Optional[str] = None
    variant_size: Optional[str] = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    item_count: int
    subtotal: int


def _get_session_id(request: Request) -> str:
    """Get or create anonymous session ID from cookie."""
    session_id = request.cookies.get("cart_session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


def _get_cart_items(
    db: Session,
    user: Optional[StoreUser],
    session_id: str,
) -> list[CartItem]:
    """Get cart items for user or session."""
    if user:
        return (
            db.query(CartItem)
            .filter(CartItem.store_user_id == user.id)
            .options(joinedload(CartItem.product), joinedload(CartItem.variant))
            .all()
        )
    return (
        db.query(CartItem)
        .filter(CartItem.session_id == session_id)
        .options(joinedload(CartItem.product), joinedload(CartItem.variant))
        .all()
    )


def _build_cart_response(items: list[CartItem]) -> CartResponse:
    """Build cart response from items."""
    cart_items = []
    for item in items:
        cart_items.append(CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            customization=item.customization,
            product_name=item.product.name if item.product else None,
            product_slug=item.product.slug if item.product else None,
            product_image=None,  # TODO: attach primary image
            variant_sku=item.variant.sku if item.variant else None,
            variant_size=item.variant.size if item.variant else None,
        ))
    return CartResponse(
        items=cart_items,
        item_count=sum(i.quantity for i in items),
        subtotal=sum(i.unit_price * i.quantity for i in items),
    )


@router.get("", response_model=CartResponse)
async def get_cart(
    request: Request,
    user: Optional[StoreUser] = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Get current cart contents."""
    session_id = _get_session_id(request)
    items = _get_cart_items(db, user, session_id)
    return _build_cart_response(items)


@router.post("/items", response_model=CartResponse)
async def add_to_cart(
    data: AddToCartRequest,
    request: Request,
    user: Optional[StoreUser] = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Add an item to the cart."""
    session_id = _get_session_id(request)

    # Validate product exists
    product = db.query(Product).filter(
        Product.id == data.product_id, Product.is_active == True
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check for existing item with same product/variant/customization
    existing_query = db.query(CartItem).filter(CartItem.product_id == data.product_id)
    if data.variant_id:
        existing_query = existing_query.filter(CartItem.variant_id == data.variant_id)
    if user:
        existing_query = existing_query.filter(CartItem.store_user_id == user.id)
    else:
        existing_query = existing_query.filter(CartItem.session_id == session_id)

    # Only merge if no customization (customized items are always unique)
    if not data.customization:
        existing = existing_query.filter(CartItem.customization == None).first()
        if existing:
            existing.quantity += data.quantity
            db.commit()
            items = _get_cart_items(db, user, session_id)
            return _build_cart_response(items)

    # Create new cart item
    cart_item = CartItem(
        store_user_id=user.id if user else None,
        session_id=session_id if not user else None,
        product_id=data.product_id,
        variant_id=data.variant_id,
        quantity=data.quantity,
        unit_price=product.base_price,
        customization=data.customization,
    )
    db.add(cart_item)
    db.commit()

    items = _get_cart_items(db, user, session_id)
    return _build_cart_response(items)


@router.put("/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    item_id: str,
    data: UpdateCartItemRequest,
    request: Request,
    user: Optional[StoreUser] = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Update cart item quantity."""
    session_id = _get_session_id(request)

    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Verify ownership
    if user and item.store_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your cart item")
    if not user and item.session_id != session_id:
        raise HTTPException(status_code=403, detail="Not your cart item")

    if data.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = data.quantity

    db.commit()
    items = _get_cart_items(db, user, session_id)
    return _build_cart_response(items)


@router.delete("/items/{item_id}", response_model=CartResponse)
async def remove_cart_item(
    item_id: str,
    request: Request,
    user: Optional[StoreUser] = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Remove item from cart."""
    session_id = _get_session_id(request)

    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if user and item.store_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your cart item")
    if not user and item.session_id != session_id:
        raise HTTPException(status_code=403, detail="Not your cart item")

    db.delete(item)
    db.commit()

    items = _get_cart_items(db, user, session_id)
    return _build_cart_response(items)


@router.post("/merge")
async def merge_cart(
    request: Request,
    user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Merge anonymous cart into user cart after login."""
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in")

    session_id = _get_session_id(request)
    anonymous_items = (
        db.query(CartItem)
        .filter(CartItem.session_id == session_id)
        .all()
    )

    for item in anonymous_items:
        item.store_user_id = user.id
        item.session_id = None

    db.commit()
    return {"message": f"Merged {len(anonymous_items)} items"}


@router.delete("")
async def clear_cart(
    request: Request,
    user: Optional[StoreUser] = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Clear all items from cart."""
    session_id = _get_session_id(request)

    if user:
        db.query(CartItem).filter(CartItem.store_user_id == user.id).delete()
    else:
        db.query(CartItem).filter(CartItem.session_id == session_id).delete()

    db.commit()
    return {"message": "Cart cleared"}
