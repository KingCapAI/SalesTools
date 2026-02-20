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
from ..services.gemini_service import generate_design
from ..services.storage_service import save_generated_image
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


@router.post("/{design_id}/regenerate", response_model=DesignVersionResponse)
async def regenerate_design(
    design_id: str,
    version_id: Optional[str] = Query(None, description="Specific version to retry. If not provided, retries using original inputs."),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """
    Retry generating a design version.

    If version_id is provided, retries that specific version using its stored prompt.
    If version_id is not provided, generates a fresh version using the original design inputs.
    """
    from ..services.gemini_service import generate_revision

    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    # Don't regenerate custom designs through this endpoint
    if design.design_type == "custom":
        raise HTTPException(
            status_code=400,
            detail="Use the custom designs endpoint to regenerate custom designs"
        )

    new_version_number = design.current_version + 1

    try:
        # If a specific version is provided, retry that version's generation
        if version_id:
            target_version = db.query(DesignVersion).filter(
                DesignVersion.id == version_id,
                DesignVersion.design_id == design_id
            ).first()

            if not target_version:
                raise HTTPException(status_code=404, detail="Version not found")

            # For version 1, regenerate with original inputs
            if target_version.version_number == 1:
                style_directions = design.style_directions.split(",") if design.style_directions else ["modern"]
                style_description = " and ".join(style_directions)

                result = await generate_design(
                    customer_name=design.brand_name,
                    hat_style=design.hat_style,
                    material=design.material,
                    style_direction=style_description,
                    custom_description=design.custom_description,
                    structure=design.structure,
                    closure=design.closure,
                    logo_path=design.logo_path,
                    brand_assets=[],
                )
            else:
                # For revisions (v2+), we need to get the version before it for context
                previous_version = db.query(DesignVersion).filter(
                    DesignVersion.design_id == design_id,
                    DesignVersion.version_number == target_version.version_number - 1
                ).first()

                # Re-run generation with the stored prompt and previous image
                result = await generate_revision(
                    original_prompt=target_version.prompt,
                    revision_notes="",  # The prompt already contains the revision
                    original_image_path=previous_version.image_path if previous_version else None,
                    logo_path=design.logo_path,
                    brand_assets=[],
                )
        else:
            # No version specified - generate fresh with original inputs
            style_directions = design.style_directions.split(",") if design.style_directions else ["modern"]
            style_description = " and ".join(style_directions)

            result = await generate_design(
                customer_name=design.brand_name,
                hat_style=design.hat_style,
                material=design.material,
                style_direction=style_description,
                custom_description=design.custom_description,
                structure=design.structure,
                closure=design.closure,
                logo_path=design.logo_path,
                brand_assets=[],
            )

        # Create version record
        version = DesignVersion(
            design_id=design.id,
            version_number=new_version_number,
            prompt=result.get("prompt", ""),
        )

        if result.get("success") and result.get("image_data"):
            image_path = await save_generated_image(
                image_data=result["image_data"],
                design_id=design.id,
                version_number=new_version_number,
            )
            version.image_path = image_path
            version.generation_status = "completed"
        else:
            version.generation_status = "failed"
            version.error_message = result.get("error", "Unknown error")

        db.add(version)

        # Update design's current version
        design.current_version = new_version_number
        design.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(version)

        return version

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate design: {str(e)}")


@router.post("/{design_id}/duplicate", response_model=DesignResponse)
async def duplicate_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """
    Create a new design with the same inputs as an existing design.

    This creates a completely separate design entry with a fresh v1 generation.
    """
    from ..schemas.design import DesignCreate, HatStyle, Material, StyleDirection, HatStructure, ClosureType

    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    # Don't duplicate custom designs through this endpoint
    if design.design_type == "custom":
        raise HTTPException(
            status_code=400,
            detail="Use the custom designs endpoint to duplicate custom designs"
        )

    try:
        # Reconstruct style directions from stored string
        style_directions_str = design.style_directions.split(",") if design.style_directions else ["modern"]
        style_directions = [StyleDirection(sd) for sd in style_directions_str]

        # Create the new design using the same inputs
        design_data = DesignCreate(
            customer_name=design.customer_name,
            brand_name=design.brand_name,
            design_name=design.design_name,
            hat_style=HatStyle(design.hat_style),
            material=Material(design.material),
            structure=HatStructure(design.structure) if design.structure else None,
            closure=ClosureType(design.closure) if design.closure else None,
            style_directions=style_directions,
            custom_description=design.custom_description,
            logo_path=design.logo_path,
        )

        new_design = await create_design(
            db=db,
            design_data=design_data,
            user_id=user.id,
        )

        return get_design_with_versions(db, new_design.id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate design: {str(e)}")


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
