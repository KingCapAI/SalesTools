"""Design management routes."""

import asyncio
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

import json as json_module
from ..database import get_db, engine
from ..models import Design, DesignVersion, DesignChat
from ..models.design import DesignLogo
from ..schemas.design import (
    DesignCreate,
    DesignUpdate,
    DesignResponse,
    DesignListResponse,
    DesignVersionResponse,
    DesignChatCreate,
    DesignChatResponse,
    DesignLogoCreate,
    RevisionCreate,
)
from ..services.design_service import (
    create_design,
    update_design,
    create_revision,
    get_design_with_versions,
    search_designs,
    VERSIONS_PER_BATCH,
)
from ..services.gemini_service import generate_design, extract_decorations_from_image
from ..services.storage_service import save_generated_image, read_file_bytes
from ..utils.dependencies import require_auth, get_current_user

router = APIRouter(prefix="/designs", tags=["Designs"])


async def _extract_decorations_background(version_ids: list[str]):
    """Background task: extract decoration methods from generated images and save to DB."""
    from sqlalchemy.orm import Session as DBSession
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)

    for vid in version_ids:
        try:
            db = SessionLocal()
            version = db.query(DesignVersion).filter(DesignVersion.id == vid).first()
            if not version or not version.image_path or version.generation_status != "completed":
                db.close()
                continue

            # Read the image from storage
            image_bytes = await read_file_bytes(version.image_path)
            if not image_bytes:
                db.close()
                continue

            import base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            decorations = await extract_decorations_from_image(image_b64)
            if decorations:
                version.detected_decorations = json_module.dumps(decorations)
                db.commit()
                print(f"[DecorationExtract] Saved decorations for version {vid}: {decorations}")
            db.close()
        except Exception as e:
            print(f"[DecorationExtract] Error for version {vid}: {e}")


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
    """Create a new design and generate 3 version options."""
    try:
        design = await create_design(
            db=db,
            design_data=design_data,
            user_id=user.id,
        )

        # Fire background decoration extraction
        completed_ids = [v.id for v in design.versions if v.generation_status == "completed"]
        if completed_ids:
            asyncio.create_task(_extract_decorations_background(completed_ids))

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
    """Get a design with all versions, logos, and chat history."""
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


@router.post("/{design_id}/regenerate", response_model=List[DesignVersionResponse])
async def regenerate_design_endpoint(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """
    Generate 3 new design versions using the original inputs.
    Resets version selection so user must choose again.
    """
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    if design.design_type == "custom":
        raise HTTPException(
            status_code=400,
            detail="Use the custom designs endpoint to regenerate custom designs"
        )

    try:
        # Get design's logos
        design_logos = db.query(DesignLogo).filter(
            DesignLogo.design_id == design_id
        ).order_by(DesignLogo.sort_order).all()

        logos_data = [
            {"name": l.name, "logo_path": l.logo_path, "location": l.location}
            for l in design_logos
        ] if design_logos else None

        # Build style description from stored directions
        style_directions = design.style_directions.split(",") if design.style_directions else ["modern"]
        style_description = " and ".join(style_directions)

        # Get next batch number
        max_batch = db.query(func.max(DesignVersion.batch_number)).filter(
            DesignVersion.design_id == design_id
        ).scalar() or 0
        new_batch = max_batch + 1

        current_max_version = design.current_version

        # Fire 3 parallel generations
        tasks = []
        for i in range(VERSIONS_PER_BATCH):
            tasks.append(
                generate_design(
                    customer_name=design.brand_name,
                    hat_style=design.hat_style,
                    material=design.material,
                    style_direction=style_description,
                    custom_description=design.custom_description,
                    structure=design.structure,
                    closure=design.closure,
                    logos=design_logos if design_logos else None,
                    logos_data=logos_data,
                    logo_path=design.logo_path if not design_logos else None,
                    brand_assets=[],
                    variation_index=i,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        versions = []
        for i, result in enumerate(results):
            v_num = current_max_version + i + 1
            is_exception = isinstance(result, Exception)

            version = DesignVersion(
                design_id=design.id,
                version_number=v_num,
                batch_number=new_batch,
                prompt=result.get("prompt", "") if not is_exception else "",
            )

            if not is_exception and result.get("success") and result.get("image_data"):
                image_path = await save_generated_image(
                    image_data=result["image_data"],
                    design_id=design.id,
                    version_number=v_num,
                )
                version.image_path = image_path
                version.generation_status = "completed"
            else:
                version.generation_status = "failed"
                if is_exception:
                    version.error_message = str(result)
                else:
                    version.error_message = result.get("error", "Unknown error")

            db.add(version)
            versions.append(version)

        # Update design
        design.current_version = current_max_version + VERSIONS_PER_BATCH
        design.selected_version_id = None  # Reset selection
        design.updated_at = datetime.utcnow()

        # Clear previous selections
        db.query(DesignVersion).filter(
            DesignVersion.design_id == design_id,
            DesignVersion.is_selected == True
        ).update({"is_selected": False})

        db.commit()
        for v in versions:
            db.refresh(v)

        # Fire background decoration extraction for completed versions
        completed_ids = [v.id for v in versions if v.generation_status == "completed"]
        if completed_ids:
            asyncio.create_task(_extract_decorations_background(completed_ids))

        return versions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate design: {str(e)}")


@router.post("/{design_id}/versions/{version_id}/extract-decorations")
async def extract_version_decorations(
    design_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Manually trigger decoration extraction for a specific version."""
    import base64

    version = db.query(DesignVersion).filter(
        DesignVersion.id == version_id,
        DesignVersion.design_id == design_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    if not version.image_path:
        raise HTTPException(status_code=400, detail="Version has no image")

    image_bytes = await read_file_bytes(version.image_path)
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Image file not found")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    decorations = await extract_decorations_from_image(image_b64)

    if decorations:
        version.detected_decorations = json_module.dumps(decorations)
        db.commit()
        return {"success": True, "decorations": decorations}
    else:
        return {"success": False, "decorations": None}


@router.get("/extract-all-decorations")
async def extract_all_existing_decorations(
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """One-time: extract decorations from all existing versions that don't have them yet."""
    versions = db.query(DesignVersion).filter(
        DesignVersion.generation_status == "completed",
        DesignVersion.image_path.isnot(None),
        DesignVersion.detected_decorations.is_(None),
    ).all()

    version_ids = [v.id for v in versions]
    if not version_ids:
        return {"message": "No versions need extraction", "count": 0}

    # Run in background
    asyncio.create_task(_extract_decorations_background(version_ids))

    return {"message": f"Started extraction for {len(version_ids)} versions", "count": len(version_ids)}


@router.post("/{design_id}/versions/{version_id}/select")
async def select_version(
    design_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Select a version as the active design. Required before requesting revisions."""
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    version = db.query(DesignVersion).filter(
        DesignVersion.id == version_id,
        DesignVersion.design_id == design_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    if version.generation_status != "completed":
        raise HTTPException(status_code=400, detail="Cannot select a failed version")

    # Clear previous selections
    db.query(DesignVersion).filter(
        DesignVersion.design_id == design_id,
        DesignVersion.is_selected == True
    ).update({"is_selected": False})

    # Set new selection
    version.is_selected = True
    design.selected_version_id = version_id
    design.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Version selected", "version_id": version_id}


@router.post("/{design_id}/duplicate", response_model=DesignResponse)
async def duplicate_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Create a new design with the same inputs and logos, generating 3 fresh versions."""
    from ..schemas.design import HatStyle, Material, StyleDirection, HatStructure, ClosureType

    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    if design.design_type == "custom":
        raise HTTPException(
            status_code=400,
            detail="Use the custom designs endpoint to duplicate custom designs"
        )

    try:
        # Reconstruct style directions
        style_directions_str = design.style_directions.split(",") if design.style_directions else ["modern"]
        style_directions = [StyleDirection(sd) for sd in style_directions_str]

        # Copy logos
        design_logos = db.query(DesignLogo).filter(
            DesignLogo.design_id == design_id
        ).order_by(DesignLogo.sort_order).all()

        logos = [
            DesignLogoCreate(
                name=l.name,
                logo_path=l.logo_path,
                logo_filename=l.logo_filename,
                location=l.location,
            )
            for l in design_logos
        ] if design_logos else None

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
            logo_path=design.logo_path if not logos else None,
            logos=logos,
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
    """Create a new revision of a design. Requires a version to be selected first."""
    # Check that a version is selected
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    if not design.selected_version_id:
        raise HTTPException(
            status_code=400,
            detail="Please select a version before requesting revisions."
        )

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
