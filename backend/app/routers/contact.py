"""Public contact form endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.store_user import StoreUser
from ..services.email_service import send_contact_form_received, send_contact_form_alert

router = APIRouter(prefix="/store/contact", tags=["Contact"])


class ContactFormSubmission(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    subject: str | None = None
    message: str


@router.post("")
async def submit_contact_form(
    data: ContactFormSubmission,
    db: Session = Depends(get_db),
):
    """Handle public contact form submission."""
    first_name = data.name.split()[0] if data.name else "there"

    # Send confirmation to the visitor
    send_contact_form_received(to_email=data.email, first_name=first_name)

    # Notify admin and salesperson staff
    staff = (
        db.query(StoreUser)
        .filter(
            StoreUser.role.in_(["admin", "salesperson"]),
            StoreUser.status == "active",
        )
        .all()
    )
    for s in staff:
        send_contact_form_alert(
            to_email=s.email,
            name=data.name,
            email=data.email,
            message=data.message,
        )

    return {"message": "Thank you for reaching out! We'll get back to you shortly."}
