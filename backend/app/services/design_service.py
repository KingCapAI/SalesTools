"""Design service for managing designs and versions."""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..models import Design, DesignVersion, DesignChat, DesignQuote
from ..models.design import DesignLogo
from ..schemas.design import DesignCreate, DesignUpdate, RevisionCreate
from .gemini_service import generate_design, generate_revision
from .storage_service import save_generated_image

# Number of parallel versions to generate per batch
VERSIONS_PER_BATCH = 3


def get_next_design_number(db: Session, brand_name: str) -> int:
    """Get the next design number for a brand."""
    max_number = (
        db.query(func.max(Design.design_number))
        .filter(Design.brand_name == brand_name)
        .scalar()
    )
    return (max_number or 0) + 1


async def create_design(
    db: Session,
    design_data: DesignCreate,
    user_id: Optional[str] = None,
) -> Design:
    """
    Create a new design and generate 3 version options in parallel.
    """
    # Convert style directions list to comma-separated string
    style_directions_str = ",".join([sd.value for sd in design_data.style_directions])

    # Create design record
    design_number = get_next_design_number(db, design_data.brand_name)
    design = Design(
        customer_name=design_data.customer_name,
        brand_name=design_data.brand_name,
        design_name=design_data.design_name,
        design_number=design_number,
        hat_style=design_data.hat_style.value,
        material=design_data.material.value,
        structure=design_data.structure.value if design_data.structure else None,
        closure=design_data.closure.value if design_data.closure else None,
        style_directions=style_directions_str,
        custom_description=design_data.custom_description,
        logo_path=design_data.logo_path,  # Keep for backward compat
        created_by_id=user_id,
    )
    db.add(design)
    db.commit()
    db.refresh(design)

    # Save DesignLogo records if multi-logo provided
    design_logos = []
    if design_data.logos:
        for i, logo_data in enumerate(design_data.logos):
            logo = DesignLogo(
                design_id=design.id,
                name=logo_data.name,
                logo_path=logo_data.logo_path,
                logo_filename=logo_data.logo_filename,
                location=logo_data.location,
                sort_order=i,
            )
            db.add(logo)
            design_logos.append(logo)
        db.commit()
    elif design_data.logo_path:
        # Backward compat: convert single logo_path to DesignLogo
        logo = DesignLogo(
            design_id=design.id,
            name="Logo",
            logo_path=design_data.logo_path,
            logo_filename="logo",
            location=None,
            sort_order=0,
        )
        db.add(logo)
        design_logos.append(logo)
        db.commit()

    # Build logos_data for prompt builder
    logos_data = [
        {"name": l.name, "logo_path": l.logo_path, "location": l.location}
        for l in design_logos
    ] if design_logos else None

    # Combine multiple style directions for the prompt
    style_description = " and ".join([sd.value for sd in design_data.style_directions])

    # Generate 3 versions in parallel
    batch_number = 1
    tasks = []
    for i in range(VERSIONS_PER_BATCH):
        tasks.append(
            generate_design(
                customer_name=design_data.brand_name,
                hat_style=design_data.hat_style.value,
                material=design_data.material.value,
                style_direction=style_description,
                custom_description=design_data.custom_description,
                structure=design_data.structure.value if design_data.structure else None,
                closure=design_data.closure.value if design_data.closure else None,
                logos=design_logos if design_logos else None,
                logos_data=logos_data,
                logo_path=design_data.logo_path if not design_logos else None,
                brand_assets=[],
                variation_index=i,
            )
        )

    # Run all 3 generations in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results, creating 3 DesignVersion records
    for i, result in enumerate(results):
        version_number = i + 1
        is_exception = isinstance(result, Exception)

        version = DesignVersion(
            design_id=design.id,
            version_number=version_number,
            batch_number=batch_number,
            prompt=result.get("prompt", "") if not is_exception else "",
        )

        if not is_exception and result.get("success") and result.get("image_data"):
            image_path = await save_generated_image(
                image_data=result["image_data"],
                design_id=design.id,
                version_number=version_number,
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

    design.current_version = VERSIONS_PER_BATCH
    db.commit()
    db.refresh(design)

    return design


def update_design(
    db: Session,
    design_id: str,
    update_data: DesignUpdate,
) -> Optional[Design]:
    """Update design metadata (name, approval status, shared status)."""
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        return None

    if update_data.design_name is not None:
        design.design_name = update_data.design_name
    if update_data.approval_status is not None:
        design.approval_status = update_data.approval_status.value
    if update_data.shared_with_team is not None:
        design.shared_with_team = update_data.shared_with_team

    design.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(design)
    return design


async def create_revision(
    db: Session,
    design_id: str,
    revision_data: RevisionCreate,
    user_id: Optional[str] = None,
) -> DesignVersion:
    """
    Create a new revision of an existing design based on the selected version.
    """
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise ValueError("Design not found")

    # Use selected version as the base for revision
    if design.selected_version_id:
        base_version = db.query(DesignVersion).filter(
            DesignVersion.id == design.selected_version_id
        ).first()
    else:
        # Fallback: use latest completed version
        base_version = (
            db.query(DesignVersion)
            .filter(
                DesignVersion.design_id == design_id,
                DesignVersion.generation_status == "completed",
            )
            .order_by(DesignVersion.version_number.desc())
            .first()
        )

    if not base_version:
        raise ValueError("No existing version found to revise")

    # Add chat message for the revision request
    chat_message = DesignChat(
        design_id=design_id,
        message=revision_data.revision_notes,
        is_user=True,
        user_id=user_id,
    )
    db.add(chat_message)

    # Generate revision based on selected version
    new_version_number = design.current_version + 1
    result = await generate_revision(
        original_prompt=base_version.prompt,
        revision_notes=revision_data.revision_notes,
        original_image_path=base_version.image_path,
        logo_path=None,
        brand_assets=[],
    )

    # Get next batch number
    max_batch = db.query(func.max(DesignVersion.batch_number)).filter(
        DesignVersion.design_id == design_id
    ).scalar() or 0

    # Create new version record
    version = DesignVersion(
        design_id=design.id,
        version_number=new_version_number,
        batch_number=max_batch + 1,
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

        ai_response = DesignChat(
            design_id=design_id,
            message=f"Failed to generate revision: {result.get('error', 'Unknown error')}",
            is_user=False,
        )
        db.add(ai_response)

    db.add(version)

    # Update design
    design.current_version = new_version_number
    design.selected_version_id = version.id  # Auto-select the revision
    design.updated_at = datetime.utcnow()

    # Mark revision as selected
    version.is_selected = True

    chat_message.version_id = version.id

    db.commit()
    db.refresh(version)

    return version


def get_design_with_versions(db: Session, design_id: str) -> Optional[Dict[str, Any]]:
    """Get a design with all its versions, logos, and chat history."""
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        return None

    # Parse style_directions from comma-separated string to list
    style_directions = design.style_directions.split(",") if design.style_directions else []

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
        "selected_version_id": design.selected_version_id,
        "hat_style": design.hat_style,
        "material": design.material,
        "structure": design.structure,
        "closure": design.closure,
        "style_directions": style_directions,
        "custom_description": design.custom_description,
        "status": design.status,
        "approval_status": design.approval_status,
        "shared_with_team": design.shared_with_team,
        "created_by_id": design.created_by_id,
        "created_at": design.created_at,
        "updated_at": design.updated_at,
        "versions": design.versions,
        "chats": design.chats,
        "logos": design.logos,
        "quote_summary": quote_summary,
    }


def get_designs_for_brand(
    db: Session,
    brand_name: str,
    skip: int = 0,
    limit: int = 50,
) -> List[Design]:
    """Get all designs for a brand."""
    return (
        db.query(Design)
        .filter(Design.brand_name == brand_name)
        .order_by(Design.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def search_designs(
    db: Session,
    brand_name: Optional[str] = None,
    customer_name: Optional[str] = None,
    approval_status: Optional[str] = None,
    user_id: Optional[str] = None,
    include_shared: bool = False,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Search designs with filters."""
    query = db.query(Design)

    # Filter by user
    if user_id:
        if include_shared:
            query = query.filter(
                or_(
                    Design.created_by_id == user_id,
                    Design.shared_with_team == True
                )
            )
        else:
            query = query.filter(Design.created_by_id == user_id)

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
        # Prefer selected version image, fallback to latest completed
        if design.selected_version_id:
            selected_version = db.query(DesignVersion).filter(
                DesignVersion.id == design.selected_version_id,
                DesignVersion.generation_status == "completed",
            ).first()
            latest_image_path = selected_version.image_path if selected_version else None
        else:
            latest_image_path = None

        if not latest_image_path:
            latest_version = (
                db.query(DesignVersion)
                .filter(
                    DesignVersion.design_id == design.id,
                    DesignVersion.generation_status == "completed",
                )
                .order_by(DesignVersion.version_number.desc())
                .first()
            )
            latest_image_path = latest_version.image_path if latest_version else None

        style_directions = design.style_directions.split(",") if design.style_directions else []

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
            "style_directions": style_directions,
            "status": design.status,
            "approval_status": design.approval_status,
            "shared_with_team": design.shared_with_team,
            "created_at": design.created_at,
            "updated_at": design.updated_at,
            "latest_image_path": latest_image_path,
            "quote_summary": quote_summary,
        })

    return results
