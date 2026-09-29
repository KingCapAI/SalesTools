"""Editable content for internal HQ pages.

GET  /api/content/{key}  any signed-in HQ user; returns the stored payload (or the
                          bundled default) plus whether the caller may edit it.
PUT  /api/content/{key}  editors only (see Settings.content_editor_emails).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import User
from ..models.site_content import SiteContent
from ..utils.dependencies import require_auth

router = APIRouter(prefix="/content", tags=["Site Content"])

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Content keys this endpoint will serve, mapped to their bundled default file.
DEFAULTS = {
    "marketing-calendar-2027": DATA_DIR / "marketing_calendar_2027.json",
}


class ContentResponse(BaseModel):
    key: str
    data: Any
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    can_edit: bool


class ContentUpdate(BaseModel):
    data: Any


def editor_emails() -> set[str]:
    raw = get_settings().content_editor_emails or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def can_edit(user: User) -> bool:
    return (user.email or "").lower() in editor_emails()


def _load_default(key: str) -> Any:
    path = DEFAULTS[key]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/{key}", response_model=ContentResponse)
async def get_content(key: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    if key not in DEFAULTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown content key")
    row = db.query(SiteContent).filter(SiteContent.key == key).first()
    if row:
        return ContentResponse(
            key=key,
            data=json.loads(row.data),
            updated_at=row.updated_at,
            updated_by=row.updated_by,
            can_edit=can_edit(user),
        )
    return ContentResponse(key=key, data=_load_default(key), can_edit=can_edit(user))


@router.put("/{key}", response_model=ContentResponse)
async def update_content(
    key: str,
    body: ContentUpdate,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if key not in DEFAULTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown content key")
    if not can_edit(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have edit access to this content")
    if not isinstance(body.data, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="data must be an object")

    row = db.query(SiteContent).filter(SiteContent.key == key).first()
    if row is None:
        row = SiteContent(key=key)
        db.add(row)
    row.data = json.dumps(body.data, ensure_ascii=False)
    row.updated_by = user.email
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ContentResponse(
        key=key, data=json.loads(row.data), updated_at=row.updated_at, updated_by=row.updated_by, can_edit=True
    )


@router.post("/{key}/reset", response_model=ContentResponse)
async def reset_content(key: str, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """Editors only: drop the stored copy and go back to the bundled default."""
    if key not in DEFAULTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown content key")
    if not can_edit(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have edit access to this content")
    db.query(SiteContent).filter(SiteContent.key == key).delete()
    db.commit()
    return ContentResponse(key=key, data=_load_default(key), can_edit=True)
