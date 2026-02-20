"""Custom design management routes."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import uuid
import os

from ..database import get_db
from ..models import Design, DesignVersion, DesignChat, DesignQuote, DesignLocationLogo
from ..schemas.custom_design import (
    CustomDesignCreate,
    CustomDesignUpdate,
    CustomDesignResponse,
    CustomDesignListResponse,
    LocationLogoResponse,
    LocationLogoUploadResponse,
    ReferenceHatUploadResponse,
)
from ..schemas.design import DesignVersionResponse, DesignChatCreate, DesignChatResponse, RevisionCreate
from ..services.gemini_service import generate_custom_design
from ..services.storage_service import save_generated_image
from ..utils.dependencies import require_auth, get_current_user
from ..config import get_settings

settings = get_settings()

router = APIRouter(prefix="/custom-designs", tags=["Custom Designs"])


def get_next_design_number(db: Session, brand_name: str) -> int:
    """Get the next design number for a brand (shared with regular designs)."""
    max_number = (
        db.query(func.max(Design.design_number))
        .filter(Design.brand_name == brand_name)
        .scalar()
    )
    return (max_number or 0) + 1


def get_custom_design_with_details(db: Session, design_id: str) -> Optional[dict]:
    """Get a custom design with all its details."""
    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        return None

    # Get quote summary if exists
    quote = db.query(DesignQuote).filter(DesignQuote.design_id == design_id).first()
    quote_summary = None
    if quote:
        quote_summary = {
            "id": quote.id,
            "quote_type": quote.quote_type,
            "quantity": quote.quantity,
            "cached_total": quote.cached_total / 100 if quote.cached_total else None,
            "cached_per_piece": quote.cached_per_piece / 100 if quote.cached_per_piece else None,
            "updated_at": quote.updated_at,
        }

    return {
        "id": design.id,
        "customer_name": design.customer_name,
        "brand_name": design.brand_name,
        "design_name": design.design_name,
        "design_number": design.design_number,
        "current_version": design.current_version,
        "hat_style": design.hat_style,
        "material": design.material,
        "structure": design.structure,
        "closure": design.closure,
        "crown_color": design.crown_color,
        "visor_color": design.visor_color,
        "design_type": design.design_type,
        "reference_hat_path": design.reference_hat_path,
        "status": design.status,
        "approval_status": design.approval_status,
        "shared_with_team": design.shared_with_team,
        "created_by_id": design.created_by_id,
        "created_at": design.created_at,
        "updated_at": design.updated_at,
        "location_logos": design.location_logos,
        "versions": design.versions,
        "chats": design.chats,
        "quote_summary": quote_summary,
    }


@router.get("", response_model=List[CustomDesignListResponse])
async def list_custom_designs(
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
    """List custom designs for the current user."""
    query = db.query(Design).filter(Design.design_type == "custom")

    # Filter by user
    if user:
        if include_shared:
            query = query.filter(
                or_(
                    Design.created_by_id == str(user.id),
                    Design.shared_with_team == True
                )
            )
        else:
            query = query.filter(Design.created_by_id == str(user.id))

    if brand_name:
        query = query.filter(Design.brand_name.ilike(f"%{brand_name}%"))
    if customer_name:
        query = query.filter(Design.customer_name.ilike(f"%{customer_name}%"))
    if approval_status:
        query = query.filter(Design.approval_status == approval_status)
    if start_date:
        query = query.filter(Design.created_at >= start_date)
    if end_date:
        query = query.filter(Design.created_at <= end_date)

    designs = query.order_by(Design.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for design in designs:
        # Get latest version image
        latest_version = (
            db.query(DesignVersion)
            .filter(
                DesignVersion.design_id == design.id,
                DesignVersion.generation_status == "completed",
            )
            .order_by(DesignVersion.version_number.desc())
            .first()
        )

        # Get quote summary if exists
        quote = db.query(DesignQuote).filter(DesignQuote.design_id == design.id).first()
        quote_summary = None
        if quote:
            quote_summary = {
                "id": quote.id,
                "quote_type": quote.quote_type,
                "quantity": quote.quantity,
                "cached_total": quote.cached_total / 100 if quote.cached_total else None,
                "cached_per_piece": quote.cached_per_piece / 100 if quote.cached_per_piece else None,
                "updated_at": quote.updated_at,
            }

        results.append({
            "id": design.id,
            "customer_name": design.customer_name,
            "brand_name": design.brand_name,
            "design_name": design.design_name,
            "design_number": design.design_number,
            "current_version": design.current_version,
            "hat_style": design.hat_style,
            "material": design.material,
            "structure": design.structure,
            "closure": design.closure,
            "crown_color": design.crown_color,
            "visor_color": design.visor_color,
            "design_type": design.design_type,
            "reference_hat_path": design.reference_hat_path,
            "status": design.status,
            "approval_status": design.approval_status,
            "shared_with_team": design.shared_with_team,
            "created_at": design.created_at,
            "updated_at": design.updated_at,
            "latest_image_path": latest_version.image_path if latest_version else None,
            "location_logos": design.location_logos,
            "quote_summary": quote_summary,
        })

    return results


@router.post("", response_model=CustomDesignResponse)
async def create_custom_design(
    design_data: CustomDesignCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Create a new custom design and generate the first version."""
    try:
        # Create design record
        design_number = get_next_design_number(db, design_data.brand_name)
        design = Design(
            customer_name=design_data.customer_name,
            brand_name=design_data.brand_name,
            design_name=design_data.design_name,
            design_number=design_number,
            hat_style=design_data.hat_style.value,
            material=design_data.material.value,
            structure=design_data.structure.value,
            closure=design_data.closure.value,
            crown_color=design_data.crown_color,
            visor_color=design_data.visor_color,
            style_directions="custom",  # Placeholder for custom designs
            design_type="custom",
            reference_hat_path=design_data.reference_hat_path,
            created_by_id=str(user.id),
        )
        db.add(design)
        db.commit()
        db.refresh(design)

        # Create location logo records
        location_logos_data = []
        for logo_data in design_data.location_logos:
            location_logo = DesignLocationLogo(
                design_id=design.id,
                location=logo_data.location.value,
                logo_path=logo_data.logo_path,
                logo_filename=logo_data.logo_filename,
                decoration_method=logo_data.decoration_method.value,
                size=logo_data.size.value,
                size_details=logo_data.size_details,
            )
            db.add(location_logo)
            location_logos_data.append({
                "location": logo_data.location.value,
                "logo_path": logo_data.logo_path,
                "decoration_method": logo_data.decoration_method.value,
                "size": logo_data.size.value,
                "size_details": logo_data.size_details,
            })

        db.commit()

        # Generate the first version
        result = await generate_custom_design(
            brand_name=design_data.brand_name,
            hat_style=design_data.hat_style.value,
            material=design_data.material.value,
            structure=design_data.structure.value,
            closure=design_data.closure.value,
            crown_color=design_data.crown_color,
            visor_color=design_data.visor_color,
            location_logos=location_logos_data,
            reference_hat_path=design_data.reference_hat_path,
        )

        # Create version record
        version = DesignVersion(
            design_id=design.id,
            version_number=1,
            prompt=result.get("prompt", ""),
        )

        if result.get("success") and result.get("image_data"):
            # Save the generated image
            image_path = await save_generated_image(
                image_data=result["image_data"],
                design_id=design.id,
                version_number=1,
            )
            version.image_path = image_path
            version.generation_status = "completed"
        else:
            version.generation_status = "failed"
            version.error_message = result.get("error", "Unknown error")

        db.add(version)
        db.commit()
        db.refresh(design)

        return get_custom_design_with_details(db, design.id)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create custom design: {str(e)}")


@router.get("/{design_id}", response_model=CustomDesignResponse)
async def get_custom_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get a custom design with all versions and chat history."""
    design = get_custom_design_with_details(db, design_id)
    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")
    return design


@router.patch("/{design_id}", response_model=CustomDesignResponse)
async def update_custom_design(
    design_id: str,
    update_data: CustomDesignUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Update custom design metadata."""
    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

    if update_data.design_name is not None:
        design.design_name = update_data.design_name
    if update_data.approval_status is not None:
        design.approval_status = update_data.approval_status.value
    if update_data.shared_with_team is not None:
        design.shared_with_team = update_data.shared_with_team

    design.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(design)

    return get_custom_design_with_details(db, design_id)


@router.delete("/{design_id}")
async def delete_custom_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Delete a custom design and all its versions."""
    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

    db.delete(design)
    db.commit()
    return {"message": "Custom design deleted successfully"}


@router.post("/{design_id}/generate", response_model=DesignVersionResponse)
async def regenerate_custom_design(
    design_id: str,
    version_id: Optional[str] = Query(None, description="Specific version to retry. If not provided, retries using original inputs."),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """
    Retry generating a custom design version.

    If version_id is provided, retries that specific version using its stored prompt.
    If version_id is not provided, generates a fresh version using the original design inputs.
    """
    from ..services.gemini_service import generate_revision

    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

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
                # Build location logos data from existing records
                location_logos_data = []
                for logo in design.location_logos:
                    location_logos_data.append({
                        "location": logo.location,
                        "logo_path": logo.logo_path,
                        "decoration_method": logo.decoration_method,
                        "size": logo.size,
                        "size_details": logo.size_details,
                    })

                result = await generate_custom_design(
                    brand_name=design.brand_name,
                    hat_style=design.hat_style,
                    material=design.material,
                    structure=design.structure,
                    closure=design.closure,
                    crown_color=design.crown_color,
                    visor_color=design.visor_color,
                    location_logos=location_logos_data,
                    reference_hat_path=design.reference_hat_path,
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
                )
        else:
            # No version specified - generate fresh with original inputs
            location_logos_data = []
            for logo in design.location_logos:
                location_logos_data.append({
                    "location": logo.location,
                    "logo_path": logo.logo_path,
                    "decoration_method": logo.decoration_method,
                    "size": logo.size,
                    "size_details": logo.size_details,
                })

            result = await generate_custom_design(
                brand_name=design.brand_name,
                hat_style=design.hat_style,
                material=design.material,
                structure=design.structure,
                closure=design.closure,
                crown_color=design.crown_color,
                visor_color=design.visor_color,
                location_logos=location_logos_data,
                reference_hat_path=design.reference_hat_path,
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
        raise HTTPException(status_code=500, detail=f"Failed to regenerate custom design: {str(e)}")


@router.post("/{design_id}/duplicate", response_model=CustomDesignResponse)
async def duplicate_custom_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """
    Create a new custom design with the same inputs as an existing design.

    This creates a completely separate design entry with a fresh v1 generation.
    """
    from ..schemas.custom_design import (
        CustomDesignCreate,
        HatStyle,
        Material,
        HatStructure,
        ClosureType,
        LocationLogoCreate,
        DecorationLocation,
        DecorationMethod,
        LogoSize,
    )

    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

    try:
        # Build location logos from existing records
        location_logos = []
        for logo in design.location_logos:
            location_logos.append(LocationLogoCreate(
                location=DecorationLocation(logo.location),
                logo_path=logo.logo_path,
                logo_filename=logo.logo_filename,
                decoration_method=DecorationMethod(logo.decoration_method),
                size=LogoSize(logo.size),
                size_details=logo.size_details,
            ))

        # Create the new design using the same inputs
        design_data = CustomDesignCreate(
            customer_name=design.customer_name,
            brand_name=design.brand_name,
            design_name=design.design_name,
            hat_style=HatStyle(design.hat_style),
            material=Material(design.material),
            structure=HatStructure(design.structure) if design.structure else HatStructure.structured,
            closure=ClosureType(design.closure) if design.closure else ClosureType.snapback,
            crown_color=design.crown_color,
            visor_color=design.visor_color,
            location_logos=location_logos,
            reference_hat_path=design.reference_hat_path,
        )

        # Create design record
        design_number = get_next_design_number(db, design_data.brand_name)
        new_design = Design(
            customer_name=design_data.customer_name,
            brand_name=design_data.brand_name,
            design_name=design_data.design_name,
            design_number=design_number,
            hat_style=design_data.hat_style.value,
            material=design_data.material.value,
            structure=design_data.structure.value,
            closure=design_data.closure.value,
            crown_color=design_data.crown_color,
            visor_color=design_data.visor_color,
            style_directions="custom",
            design_type="custom",
            reference_hat_path=design_data.reference_hat_path,
            created_by_id=str(user.id),
        )
        db.add(new_design)
        db.commit()
        db.refresh(new_design)

        # Create location logo records
        location_logos_data = []
        for logo_data in design_data.location_logos:
            location_logo = DesignLocationLogo(
                design_id=new_design.id,
                location=logo_data.location.value,
                logo_path=logo_data.logo_path,
                logo_filename=logo_data.logo_filename,
                decoration_method=logo_data.decoration_method.value,
                size=logo_data.size.value,
                size_details=logo_data.size_details,
            )
            db.add(location_logo)
            location_logos_data.append({
                "location": logo_data.location.value,
                "logo_path": logo_data.logo_path,
                "decoration_method": logo_data.decoration_method.value,
                "size": logo_data.size.value,
                "size_details": logo_data.size_details,
            })

        db.commit()

        # Generate the first version
        result = await generate_custom_design(
            brand_name=design_data.brand_name,
            hat_style=design_data.hat_style.value,
            material=design_data.material.value,
            structure=design_data.structure.value,
            closure=design_data.closure.value,
            crown_color=design_data.crown_color,
            visor_color=design_data.visor_color,
            location_logos=location_logos_data,
            reference_hat_path=design_data.reference_hat_path,
        )

        # Create version record
        version = DesignVersion(
            design_id=new_design.id,
            version_number=1,
            prompt=result.get("prompt", ""),
        )

        if result.get("success") and result.get("image_data"):
            image_path = await save_generated_image(
                image_data=result["image_data"],
                design_id=new_design.id,
                version_number=1,
            )
            version.image_path = image_path
            version.generation_status = "completed"
        else:
            version.generation_status = "failed"
            version.error_message = result.get("error", "Unknown error")

        db.add(version)
        db.commit()
        db.refresh(new_design)

        return get_custom_design_with_details(db, new_design.id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate custom design: {str(e)}")


@router.get("/{design_id}/versions", response_model=List[DesignVersionResponse])
async def list_custom_design_versions(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all versions of a custom design."""
    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

    versions = (
        db.query(DesignVersion)
        .filter(DesignVersion.design_id == design_id)
        .order_by(DesignVersion.version_number.desc())
        .all()
    )
    return versions


@router.post("/{design_id}/versions", response_model=DesignVersionResponse)
async def create_custom_design_revision(
    design_id: str,
    revision_data: RevisionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Create a new revision of a custom design with revision notes."""
    from ..services.gemini_service import generate_revision

    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

    # Get the latest version
    latest_version = (
        db.query(DesignVersion)
        .filter(DesignVersion.design_id == design_id)
        .order_by(DesignVersion.version_number.desc())
        .first()
    )

    if not latest_version:
        raise HTTPException(status_code=400, detail="No existing version found")

    # Add chat message for the revision request
    chat_message = DesignChat(
        design_id=design_id,
        message=revision_data.revision_notes,
        is_user=True,
        user_id=str(user.id),
    )
    db.add(chat_message)

    # Generate revision
    new_version_number = design.current_version + 1
    result = await generate_revision(
        original_prompt=latest_version.prompt,
        revision_notes=revision_data.revision_notes,
        original_image_path=latest_version.image_path,
    )

    # Create new version record
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

        # Add AI response to chat
        ai_response = DesignChat(
            design_id=design_id,
            version_id=version.id,
            message=f"Generated Design #{design.design_number}v{new_version_number} based on your revision request.",
            is_user=False,
        )
        db.add(ai_response)
    else:
        version.generation_status = "failed"
        version.error_message = result.get("error", "Unknown error")

        # Add AI error response to chat
        ai_response = DesignChat(
            design_id=design_id,
            message=f"Failed to generate revision: {result.get('error', 'Unknown error')}",
            is_user=False,
        )
        db.add(ai_response)

    db.add(version)

    # Update design's current version
    design.current_version = new_version_number
    design.updated_at = datetime.utcnow()

    # Update chat message with version link
    chat_message.version_id = version.id

    db.commit()
    db.refresh(version)

    return version


@router.get("/{design_id}/chat", response_model=List[DesignChatResponse])
async def get_custom_design_chat(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get chat history for a custom design."""
    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

    chats = (
        db.query(DesignChat)
        .filter(DesignChat.design_id == design_id)
        .order_by(DesignChat.created_at)
        .all()
    )
    return chats


@router.post("/{design_id}/chat", response_model=DesignChatResponse)
async def add_custom_design_chat(
    design_id: str,
    chat_data: DesignChatCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Add a chat message to a custom design."""
    design = db.query(Design).filter(
        Design.id == design_id,
        Design.design_type == "custom"
    ).first()

    if not design:
        raise HTTPException(status_code=404, detail="Custom design not found")

    chat = DesignChat(
        design_id=design_id,
        message=chat_data.message,
        is_user=True,
        user_id=str(user.id),
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


# Upload endpoints

@router.post("/upload/location-logo", response_model=LocationLogoUploadResponse)
async def upload_location_logo(
    file: UploadFile = File(...),
    location: str = Query(..., description="Location: front, left, right, back, visor"),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Upload a logo for a specific location."""
    if location not in ["front", "left", "right", "back", "visor"]:
        raise HTTPException(status_code=400, detail="Invalid location")

    # Validate file type (SVG not supported - Gemini API only accepts PNG/JPG/WEBP)
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PNG, JPG, and WEBP images are accepted. SVG files are not supported."
        )

    # Create unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    unique_filename = f"{uuid.uuid4()}{ext}"
    relative_path = f"location_logos/{unique_filename}"
    full_path = os.path.join(settings.upload_dir, relative_path)

    # Ensure directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Save file
    contents = await file.read()
    with open(full_path, "wb") as f:
        f.write(contents)

    return {
        "logo_path": relative_path,
        "logo_filename": file.filename or unique_filename,
    }


@router.post("/upload/reference-hat", response_model=ReferenceHatUploadResponse)
async def upload_reference_hat(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Upload a reference hat image."""
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Create unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    unique_filename = f"{uuid.uuid4()}{ext}"
    relative_path = f"reference_hats/{unique_filename}"
    full_path = os.path.join(settings.upload_dir, relative_path)

    # Ensure directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Save file
    contents = await file.read()
    with open(full_path, "wb") as f:
        f.write(contents)

    return {
        "reference_hat_path": relative_path,
        "filename": file.filename or unique_filename,
    }
