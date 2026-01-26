"""Design management routes."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Design, DesignVersion, DesignChat
from ..schemas.design import (
    DesignCreate,
    DesignUpdate,
    DesignResponse,
    DesignListResponse,
    DesignVersionResponse,
    DesignChatCreate,
    DesignChatResponse,
    RevisionCreate,
)
from ..services.design_service import (
    create_design,
    update_design,
    create_revision,
    get_design_with_versions,
    search_designs,
)
from ..utils.dependencies import require_auth, get_current_user

router = APIRouter(prefix="/designs", tags=["Designs"])


@router.get("", response_model=List[DesignListResponse])
async def list_designs(
    brand_name: Optional[str] = Query(None),
    customer_name: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None),
    include_shared: bool = Query(False, description="Include designs shared with your team"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """List designs for the current user. Optionally include team-shared designs."""
    designs = search_designs(
        db=db,
        brand_name=brand_name,
        customer_name=customer_name,
        approval_status=approval_status,
        user_id=str(user.id),
        include_shared=include_shared,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return designs


@router.post("", response_model=DesignResponse)
async def create_new_design(
    design_data: DesignCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Create a new design and generate the first version."""
    try:
        design = await create_design(
            db=db,
            design_data=design_data,
            user_id=user.id,
        )
        # Convert design to response format
        return get_design_with_versions(db, design.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create design: {str(e)}")


@router.get("/{design_id}", response_model=DesignResponse)
async def get_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get a design with all versions and chat history."""
    design = get_design_with_versions(db, design_id)
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return design


@router.patch("/{design_id}", response_model=DesignResponse)
async def update_design_endpoint(
    design_id: str,
    update_data: DesignUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Update design metadata (name, approval status, shared status)."""
    design = update_design(db, design_id, update_data)
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return get_design_with_versions(db, design_id)


@router.delete("/{design_id}")
async def delete_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Delete a design and all its versions."""
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    db.delete(design)
    db.commit()
    return {"message": "Design deleted successfully"}


@router.get("/{design_id}/versions", response_model=List[DesignVersionResponse])
async def list_versions(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all versions of a design."""
    versions = (
        db.query(DesignVersion)
        .filter(DesignVersion.design_id == design_id)
        .order_by(DesignVersion.version_number.desc())
        .all()
    )
    return versions


@router.post("/{design_id}/versions", response_model=DesignVersionResponse)
async def create_version(
    design_id: str,
    revision_data: RevisionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Create a new revision of a design."""
    try:
        version = await create_revision(
            db=db,
            design_id=design_id,
            revision_data=revision_data,
            user_id=user.id,
        )
        return version
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create revision: {str(e)}")


@router.get("/{design_id}/chat", response_model=List[DesignChatResponse])
async def get_chat_history(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get chat history for a design."""
    chats = (
        db.query(DesignChat)
        .filter(DesignChat.design_id == design_id)
        .order_by(DesignChat.created_at)
        .all()
    )
    return chats


@router.post("/{design_id}/chat", response_model=DesignChatResponse)
async def add_chat_message(
    design_id: str,
    chat_data: DesignChatCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Add a chat message to a design."""
    # Verify design exists
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    chat = DesignChat(
        design_id=design_id,
        message=chat_data.message,
        is_user=True,
        user_id=user.id,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat
