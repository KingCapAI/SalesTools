"""Design service for managing designs and versions."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..models import Design, DesignVersion, DesignChat
from ..schemas.design import DesignCreate, DesignUpdate, RevisionCreate
from .gemini_service import generate_design, generate_revision
from .storage_service import save_generated_image


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
    Create a new design and generate the first version.

    Args:
        db: Database session
        design_data: Design creation data
        user_id: ID of the user creating the design

    Returns:
        The created Design object
    """
    # Convert style directions list to comma-separated string
    style_directions_str = ",".join([sd.value for sd in design_data.style_directions])

    # Create design record with text fields
    design_number = get_next_design_number(db, design_data.brand_name)
    design = Design(
        customer_name=design_data.customer_name,
        brand_name=design_data.brand_name,
        design_name=design_data.design_name,
        design_number=design_number,
        hat_style=design_data.hat_style.value,
        material=design_data.material.value,
        style_directions=style_directions_str,
        custom_description=design_data.custom_description,
        created_by_id=user_id,
    )
    db.add(design)
    db.commit()
    db.refresh(design)

    # Generate the first version using the brand name
    # Combine multiple style directions for the prompt
    style_description = " and ".join([sd.value for sd in design_data.style_directions])

    result = await generate_design(
        customer_name=design_data.brand_name,  # Use brand name for the design prompt
        hat_style=design_data.hat_style.value,
        material=design_data.material.value,
        style_direction=style_description,  # Combined style directions
        custom_description=design_data.custom_description,
        logo_path=None,
        brand_assets=[],
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
    Create a new revision of an existing design.

    Args:
        db: Database session
        design_id: ID of the design to revise
        revision_data: Revision data with notes
        user_id: ID of the user requesting revision

    Returns:
        The created DesignVersion object
    """
    # Get design
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise ValueError("Design not found")

    # Get all versions ordered by version number to build conversation history
    all_versions = (
        db.query(DesignVersion)
        .filter(DesignVersion.design_id == design_id)
        .order_by(DesignVersion.version_number.asc())
        .all()
    )

    if not all_versions:
        raise ValueError("No existing version found")

    latest_version = all_versions[-1]

    # Build conversation history from all versions
    # Each version represents a turn: user prompt -> model image response
    conversation_history = []
    for version in all_versions:
        # User turn: the prompt that was sent
        if version.prompt:
            conversation_history.append({
                "role": "user",
                "prompt": version.prompt,
            })
        # Model turn: the generated image
        if version.image_path and version.generation_status == "completed":
            conversation_history.append({
                "role": "model",
                "image_path": version.image_path,
            })

    # Add chat message for the revision request
    chat_message = DesignChat(
        design_id=design_id,
        message=revision_data.revision_notes,
        is_user=True,
        user_id=user_id,
    )
    db.add(chat_message)

    # Generate revision with full conversation history
    new_version_number = design.current_version + 1
    result = await generate_revision(
        original_prompt=latest_version.prompt,
        revision_notes=revision_data.revision_notes,
        original_image_path=latest_version.image_path,
        logo_path=None,
        brand_assets=[],
        conversation_history=conversation_history,
    )

    # Create new version record
    version = DesignVersion(
        design_id=design.id,
        version_number=new_version_number,
        prompt=result.get("prompt", ""),
    )

    if result.get("success") and result.get("image_data"):
        # Save the generated image
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


def get_design_with_versions(db: Session, design_id: str) -> Optional[Dict[str, Any]]:
    """Get a design with all its versions and chat history."""
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        return None

    # Parse style_directions from comma-separated string to list
    style_directions = design.style_directions.split(",") if design.style_directions else []

    return {
        "id": design.id,
        "customer_name": design.customer_name,
        "brand_name": design.brand_name,
        "design_name": design.design_name,
        "design_number": design.design_number,
        "current_version": design.current_version,
        "hat_style": design.hat_style,
        "material": design.material,
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
    shared_with_team: Optional[bool] = None,
    created_by_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search designs with filters.

    Returns list of designs with brand name, customer name, and latest image path.
    """
    query = db.query(Design)

    if brand_name:
        query = query.filter(Design.brand_name.ilike(f"%{brand_name}%"))
    if customer_name:
        query = query.filter(Design.customer_name.ilike(f"%{customer_name}%"))
    if approval_status:
        query = query.filter(Design.approval_status == approval_status)
    if shared_with_team is not None:
        query = query.filter(Design.shared_with_team == shared_with_team)
    if created_by_id:
        query = query.filter(Design.created_by_id == created_by_id)
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

        # Parse style_directions from comma-separated string to list
        style_directions = design.style_directions.split(",") if design.style_directions else []

        results.append({
            "id": design.id,
            "customer_name": design.customer_name,
            "brand_name": design.brand_name,
            "design_name": design.design_name,
            "design_number": design.design_number,
            "current_version": design.current_version,
            "hat_style": design.hat_style,
            "material": design.material,
            "style_directions": style_directions,
            "status": design.status,
            "approval_status": design.approval_status,
            "shared_with_team": design.shared_with_team,
            "created_at": design.created_at,
            "updated_at": design.updated_at,
            "latest_image_path": latest_version.image_path if latest_version else None,
        })

    return results
