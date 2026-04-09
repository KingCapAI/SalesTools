"""Design request routes: tracked, versioned design workflow system."""

import os
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models.design_request import (
    DesignRequest, DesignRequestVersion, DesignRequestComment, DesignRequestActivity,
)
from ..models.sample_request import SampleRequest
from ..models.store_user import StoreUser
from ..models.store_quote import Quote
from ..utils.store_dependencies import require_store_role, get_current_store_user
from ..services.email_service import send_design_request_alert, send_design_ready_for_review, send_design_feedback_alert

router = APIRouter(tags=["Design Requests"])

# Storage imports
from ..services.storage_service import save_file_bytes, generate_unique_filename


# ---------------------------------------------------------------------------
# Status workflow
# ---------------------------------------------------------------------------

VALID_STATUSES = (
    "submitted", "assigned", "in_progress", "review",
    "approved", "changes_requested", "rejected",
    "production_needed", "completed",
)

STATUS_TRANSITIONS = {
    "submitted": ("assigned",),
    "assigned": ("in_progress", "submitted"),
    "in_progress": ("review",),
    "review": ("approved", "changes_requested", "rejected"),
    "changes_requested": ("in_progress",),
    "approved": ("production_needed", "completed"),
    "production_needed": ("completed",),
    "completed": (),
    "rejected": (),
}

VALID_PRIORITIES = ("low", "normal", "high", "urgent")
VALID_DESIGN_TYPES = ("new_design", "revision", "production_file", "ai_cleanup")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DesignRequestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    design_type: str = "new_design"
    customer_id: Optional[str] = None
    customer_name: str = ""
    brand_name: str = ""
    hat_style: Optional[str] = None
    hat_color: Optional[str] = None
    decoration_locations: Optional[List[str]] = None
    decoration_methods: Optional[List[str]] = None
    linked_sample_request_id: Optional[str] = None
    linked_design_id: Optional[str] = None
    linked_quote_id: Optional[str] = None
    priority: str = "normal"
    due_date: Optional[datetime] = None


class DesignRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    internal_notes: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class AssignUpdate(BaseModel):
    assigned_to_id: Optional[str] = None  # None = self-assign


class ReviewResponse(BaseModel):
    response: str  # approved, changes_requested, rejected
    feedback: Optional[str] = None
    production_file_needed: bool = False


class CommentCreate(BaseModel):
    message: str
    attachment_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_request_number(db: Session) -> str:
    """Generate sequential DR-{YEAR}-{SEQ:05d} number."""
    year = datetime.utcnow().year
    prefix = f"DR-{year}-"

    last = (
        db.query(DesignRequest)
        .filter(DesignRequest.request_number.like(f"{prefix}%"))
        .order_by(desc(DesignRequest.request_number))
        .first()
    )

    if last:
        try:
            seq = int(last.request_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:05d}"


def _log_activity(db: Session, request_id: str, user_id: str, action: str, description: str, details: dict = None):
    """Create an audit log entry."""
    activity = DesignRequestActivity(
        design_request_id=request_id,
        user_id=user_id,
        action=action,
        description=description,
        details=json.dumps(details) if details else None,
    )
    db.add(activity)


def _build_linked_quote(dr: DesignRequest, db: Session):
    """Build linked quote summary for a design request."""
    if not dr.linked_quote_id:
        return None
    q = db.query(Quote).filter(Quote.id == dr.linked_quote_id).first()
    if not q:
        return None
    return {
        "id": q.id,
        "quote_number": q.quote_number,
        "status": q.status,
        "total": q.total,
    }


def _build_request_response(dr: DesignRequest, db: Session, include_internal: bool = False) -> dict:
    """Build full detail response for a design request."""
    # Get user names
    requested_by = db.query(StoreUser).filter(StoreUser.id == dr.requested_by_id).first()
    assigned_to = db.query(StoreUser).filter(StoreUser.id == dr.assigned_to_id).first() if dr.assigned_to_id else None

    # Build versions
    versions = []
    for v in dr.versions:
        uploader = db.query(StoreUser).filter(StoreUser.id == v.uploaded_by_id).first()
        versions.append({
            "id": v.id,
            "version_number": v.version_number,
            "file_path": v.file_path,
            "thumbnail_path": v.thumbnail_path,
            "file_type": v.file_type,
            "notes": v.notes,
            "is_production_file": v.is_production_file == "true",
            "uploaded_by_id": v.uploaded_by_id,
            "uploaded_by_name": f"{uploader.first_name} {uploader.last_name}".strip() if uploader else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        })

    # Build comments
    comments = []
    for c in dr.comments:
        commenter = db.query(StoreUser).filter(StoreUser.id == c.user_id).first()
        comments.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_name": f"{commenter.first_name} {commenter.last_name}".strip() if commenter else None,
            "user_role": commenter.role if commenter else None,
            "message": c.message,
            "attachment_path": c.attachment_path,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    # Build activities
    activities = []
    for a in dr.activities:
        actor = db.query(StoreUser).filter(StoreUser.id == a.user_id).first() if a.user_id else None
        activities.append({
            "id": a.id,
            "user_id": a.user_id,
            "user_name": f"{actor.first_name} {actor.last_name}".strip() if actor else None,
            "action": a.action,
            "description": a.description,
            "details": json.loads(a.details) if a.details else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    # Linked sample request info
    linked_sample = None
    if dr.linked_sample_request_id:
        sr = db.query(SampleRequest).filter(SampleRequest.id == dr.linked_sample_request_id).first()
        if sr:
            linked_sample = {
                "id": sr.id,
                "sample_number": sr.sample_number,
                "status": sr.status,
                "customer_name": None,  # Populated below
            }
            if sr.customer_id:
                cust = db.query(StoreUser).filter(StoreUser.id == sr.customer_id).first()
                if cust:
                    linked_sample["customer_name"] = f"{cust.first_name} {cust.last_name}".strip() or cust.company_name

    result = {
        "id": dr.id,
        "request_number": dr.request_number,
        "status": dr.status,
        "priority": dr.priority,
        "requested_by_id": dr.requested_by_id,
        "requested_by_name": f"{requested_by.first_name} {requested_by.last_name}".strip() if requested_by else None,
        "assigned_to_id": dr.assigned_to_id,
        "assigned_to_name": f"{assigned_to.first_name} {assigned_to.last_name}".strip() if assigned_to else None,
        "customer_id": dr.customer_id,
        "customer_name": dr.customer_name,
        "brand_name": dr.brand_name,
        "title": dr.title,
        "description": dr.description,
        "design_type": dr.design_type,
        "hat_style": dr.hat_style,
        "hat_color": dr.hat_color,
        "decoration_locations": json.loads(dr.decoration_locations) if dr.decoration_locations else [],
        "decoration_methods": json.loads(dr.decoration_methods) if dr.decoration_methods else [],
        "linked_sample_request_id": dr.linked_sample_request_id,
        "linked_design_id": dr.linked_design_id,
        "linked_quote_id": dr.linked_quote_id,
        "linked_sample": linked_sample,
        "linked_quote": _build_linked_quote(dr, db),
        "art_id": dr.art_id,
        "due_date": dr.due_date.isoformat() if dr.due_date else None,
        "completed_at": dr.completed_at.isoformat() if dr.completed_at else None,
        "created_at": dr.created_at.isoformat() if dr.created_at else None,
        "updated_at": dr.updated_at.isoformat() if dr.updated_at else None,
        "versions": versions,
        "comments": comments,
        "activities": activities,
    }

    if include_internal:
        result["internal_notes"] = dr.internal_notes

    return result


def _build_request_list_item(dr: DesignRequest, db: Session) -> dict:
    """Build summary for list view."""
    requested_by = db.query(StoreUser).filter(StoreUser.id == dr.requested_by_id).first()
    assigned_to = db.query(StoreUser).filter(StoreUser.id == dr.assigned_to_id).first() if dr.assigned_to_id else None

    version_count = db.query(func.count(DesignRequestVersion.id)).filter(
        DesignRequestVersion.design_request_id == dr.id
    ).scalar()

    return {
        "id": dr.id,
        "request_number": dr.request_number,
        "title": dr.title,
        "status": dr.status,
        "priority": dr.priority,
        "design_type": dr.design_type,
        "customer_name": dr.customer_name,
        "brand_name": dr.brand_name,
        "requested_by_name": f"{requested_by.first_name} {requested_by.last_name}".strip() if requested_by else None,
        "assigned_to_name": f"{assigned_to.first_name} {assigned_to.last_name}".strip() if assigned_to else None,
        "version_count": version_count,
        "due_date": dr.due_date.isoformat() if dr.due_date else None,
        "created_at": dr.created_at.isoformat() if dr.created_at else None,
    }


# ===========================================================================
# SALESPERSON ENDPOINTS — /sales/design-requests/*
# ===========================================================================

@router.get("/sales/design-requests")
async def sales_list_design_requests(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """List design requests created by the current salesperson."""
    query = db.query(DesignRequest).filter(DesignRequest.requested_by_id == user.id)

    if status:
        query = query.filter(DesignRequest.status == status)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            DesignRequest.request_number.ilike(term),
            DesignRequest.title.ilike(term),
            DesignRequest.customer_name.ilike(term),
            DesignRequest.brand_name.ilike(term),
        ))

    requests = query.order_by(desc(DesignRequest.created_at)).limit(limit).all()
    return [_build_request_list_item(dr, db) for dr in requests]


@router.post("/sales/design-requests")
async def sales_create_design_request(
    data: DesignRequestCreate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """Create a new design request."""
    if data.design_type not in VALID_DESIGN_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid design_type. Must be one of: {', '.join(VALID_DESIGN_TYPES)}")
    if data.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")

    # Validate linked sample request
    if data.linked_sample_request_id:
        sr = db.query(SampleRequest).filter(SampleRequest.id == data.linked_sample_request_id).first()
        if not sr:
            raise HTTPException(status_code=404, detail="Linked sample request not found")

    request_number = _generate_request_number(db)

    dr = DesignRequest(
        request_number=request_number,
        status="submitted",
        priority=data.priority,
        requested_by_id=user.id,
        customer_id=data.customer_id,
        customer_name=data.customer_name,
        brand_name=data.brand_name,
        title=data.title,
        description=data.description,
        design_type=data.design_type,
        hat_style=data.hat_style,
        hat_color=data.hat_color,
        decoration_locations=json.dumps(data.decoration_locations) if data.decoration_locations else None,
        decoration_methods=json.dumps(data.decoration_methods) if data.decoration_methods else None,
        linked_sample_request_id=data.linked_sample_request_id,
        linked_design_id=data.linked_design_id,
        linked_quote_id=data.linked_quote_id,
        due_date=data.due_date,
    )
    db.add(dr)
    db.flush()

    _log_activity(db, dr.id, user.id, "created", f"Design request {request_number} created")
    db.commit()
    db.refresh(dr)

    # Notify design managers about the new request
    design_managers = db.query(StoreUser).filter(
        StoreUser.role.in_(["design_manager", "admin"]),
        StoreUser.status == "active",
    ).all()
    for dm in design_managers:
        send_design_request_alert(
            to_email=dm.email,
            request_number=request_number,
            customer_name=data.customer_name or "N/A",
            details=data.title,
        )

    return _build_request_response(dr, db)


@router.get("/sales/design-requests/{request_id}")
async def sales_get_design_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """Get full detail for a design request."""
    dr = db.query(DesignRequest).filter(
        DesignRequest.id == request_id,
        DesignRequest.requested_by_id == user.id,
    ).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    return _build_request_response(dr, db)


@router.put("/sales/design-requests/{request_id}")
async def sales_update_design_request(
    request_id: str,
    data: DesignRequestUpdate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """Update a design request (only when submitted)."""
    dr = db.query(DesignRequest).filter(
        DesignRequest.id == request_id,
        DesignRequest.requested_by_id == user.id,
    ).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    if dr.status not in ("submitted", "assigned"):
        raise HTTPException(status_code=400, detail="Can only update requests in submitted or assigned status")

    if data.title is not None:
        dr.title = data.title
    if data.description is not None:
        dr.description = data.description
    if data.priority is not None:
        if data.priority not in VALID_PRIORITIES:
            raise HTTPException(status_code=400, detail=f"Invalid priority")
        dr.priority = data.priority
    if data.due_date is not None:
        dr.due_date = data.due_date

    dr.updated_at = datetime.utcnow()
    _log_activity(db, dr.id, user.id, "updated", "Design request updated by salesperson")
    db.commit()
    db.refresh(dr)

    return _build_request_response(dr, db)


@router.post("/sales/design-requests/{request_id}/review")
async def sales_review_design(
    request_id: str,
    data: ReviewResponse,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """Approve, request changes, or reject a design version."""
    dr = db.query(DesignRequest).filter(
        DesignRequest.id == request_id,
        DesignRequest.requested_by_id == user.id,
    ).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    if dr.status != "review":
        raise HTTPException(status_code=400, detail="Design request is not in review status")

    if data.response == "approved":
        if data.production_file_needed:
            dr.status = "production_needed"
        else:
            dr.status = "completed"
            dr.completed_at = datetime.utcnow()
        # Generate art_id on approval
        year = datetime.utcnow().year
        art_prefix = f"ART-{year}-"
        last_art = (
            db.query(DesignRequest)
            .filter(DesignRequest.art_id.like(f"{art_prefix}%"))
            .order_by(desc(DesignRequest.art_id))
            .first()
        )
        if last_art and last_art.art_id:
            try:
                art_seq = int(last_art.art_id.split("-")[-1]) + 1
            except ValueError:
                art_seq = 1
        else:
            art_seq = 1
        dr.art_id = f"{art_prefix}{art_seq:05d}"
    elif data.response == "changes_requested":
        dr.status = "changes_requested"
    elif data.response == "rejected":
        dr.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="response must be: approved, changes_requested, or rejected")

    dr.updated_at = datetime.utcnow()

    desc_text = f"Salesperson reviewed: {data.response}"
    if data.feedback:
        desc_text += f" — {data.feedback}"
    _log_activity(db, dr.id, user.id, "review", desc_text, {"response": data.response, "feedback": data.feedback})

    # Add feedback as a comment
    if data.feedback:
        comment = DesignRequestComment(
            design_request_id=dr.id,
            user_id=user.id,
            message=f"[Review: {data.response.replace('_', ' ').title()}] {data.feedback}",
        )
        db.add(comment)

    db.commit()
    db.refresh(dr)
    return _build_request_response(dr, db)


@router.post("/sales/design-requests/{request_id}/comments")
async def sales_add_comment(
    request_id: str,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """Add a comment to a design request."""
    dr = db.query(DesignRequest).filter(
        DesignRequest.id == request_id,
        DesignRequest.requested_by_id == user.id,
    ).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    comment = DesignRequestComment(
        design_request_id=dr.id,
        user_id=user.id,
        message=data.message,
        attachment_path=data.attachment_path,
    )
    db.add(comment)
    _log_activity(db, dr.id, user.id, "comment", "Comment added by salesperson")
    db.commit()
    db.refresh(comment)

    return {"id": comment.id, "message": comment.message, "created_at": comment.created_at.isoformat()}


@router.post("/sales/design-requests/upload")
async def sales_upload_reference(
    file: UploadFile = File(...),
    user: StoreUser = Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """Upload a reference file for a design request."""
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"
    unique_name = generate_unique_filename(f"upload{ext}")
    contents = await file.read()
    relative_path = await save_file_bytes(contents, "design_requests/references", unique_name, file.content_type or "application/octet-stream")
    return {"file_path": relative_path, "filename": file.filename}


# ===========================================================================
# DESIGNER ENDPOINTS — /design/requests/*
# ===========================================================================

@router.get("/design/requests")
async def designer_list_requests(
    status: Optional[str] = Query(None),
    assigned_to_me: bool = Query(False),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """List design requests (designer queue)."""
    query = db.query(DesignRequest)

    if assigned_to_me:
        query = query.filter(DesignRequest.assigned_to_id == user.id)
    if status:
        query = query.filter(DesignRequest.status == status)
    if priority:
        query = query.filter(DesignRequest.priority == priority)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            DesignRequest.request_number.ilike(term),
            DesignRequest.title.ilike(term),
            DesignRequest.customer_name.ilike(term),
            DesignRequest.brand_name.ilike(term),
        ))

    # Priority ordering: urgent first, then by created_at
    priority_order = func.CASE(
        (DesignRequest.priority == "urgent", 0),
        (DesignRequest.priority == "high", 1),
        (DesignRequest.priority == "normal", 2),
        (DesignRequest.priority == "low", 3),
        else_=4,
    )
    requests = query.order_by(priority_order, desc(DesignRequest.created_at)).limit(limit).all()
    return [_build_request_list_item(dr, db) for dr in requests]


@router.get("/design/requests/{request_id}")
async def designer_get_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """Get full detail for a design request."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    return _build_request_response(dr, db, include_internal=True)


@router.put("/design/requests/{request_id}/assign")
async def designer_assign_request(
    request_id: str,
    data: AssignUpdate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """Self-assign or assign to another designer."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    assignee_id = data.assigned_to_id or user.id
    assignee = db.query(StoreUser).filter(StoreUser.id == assignee_id).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    dr.assigned_to_id = assignee_id
    if dr.status == "submitted":
        dr.status = "assigned"
    dr.updated_at = datetime.utcnow()

    assignee_name = f"{assignee.first_name} {assignee.last_name}".strip()
    _log_activity(db, dr.id, user.id, "assigned", f"Assigned to {assignee_name}")
    db.commit()
    db.refresh(dr)

    return _build_request_response(dr, db, include_internal=True)


@router.put("/design/requests/{request_id}/status")
async def designer_update_status(
    request_id: str,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """Update design request status."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")

    allowed = STATUS_TRANSITIONS.get(dr.status, ())
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{dr.status}' to '{data.status}'. Allowed: {', '.join(allowed)}",
        )

    old_status = dr.status
    dr.status = data.status
    dr.updated_at = datetime.utcnow()

    if data.status == "completed":
        dr.completed_at = datetime.utcnow()

    desc_text = f"Status changed: {old_status} → {data.status}"
    if data.notes:
        desc_text += f" — {data.notes}"
    _log_activity(db, dr.id, user.id, "status_change", desc_text, {"from": old_status, "to": data.status})

    db.commit()
    db.refresh(dr)

    # Send notifications on key status changes
    if data.status == "review":
        # Notify the salesperson who requested the design
        requester = db.query(StoreUser).filter(StoreUser.id == dr.requested_by_id).first()
        if requester and requester.email:
            send_design_ready_for_review(
                to_email=requester.email,
                first_name=requester.first_name,
                request_number=dr.request_number,
            )
    elif data.status == "changes_requested" and data.notes:
        # Notify design managers about the feedback
        design_managers = db.query(StoreUser).filter(
            StoreUser.role.in_(["design_manager", "admin"]),
            StoreUser.status == "active",
        ).all()
        for dm in design_managers:
            send_design_feedback_alert(
                to_email=dm.email,
                request_number=dr.request_number,
                feedback=data.notes,
            )

    return _build_request_response(dr, db, include_internal=True)


@router.post("/design/requests/{request_id}/versions")
async def designer_upload_version(
    request_id: str,
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """Upload a new design version."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    if dr.status not in ("assigned", "in_progress", "changes_requested"):
        raise HTTPException(status_code=400, detail="Cannot upload versions in current status")

    # Save file
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"
    file_type = ext.lstrip(".")
    unique_name = generate_unique_filename(f"upload{ext}")
    contents = await file.read()
    relative_path = await save_file_bytes(contents, f"design_requests/versions/{request_id}", unique_name, file.content_type or "application/octet-stream")

    # Determine version number
    max_version = db.query(func.max(DesignRequestVersion.version_number)).filter(
        DesignRequestVersion.design_request_id == request_id,
        DesignRequestVersion.is_production_file == "false",
    ).scalar() or 0

    version = DesignRequestVersion(
        design_request_id=request_id,
        version_number=max_version + 1,
        file_path=relative_path,
        thumbnail_path=relative_path if file_type in ("png", "jpg", "jpeg", "webp") else None,
        file_type=file_type,
        notes=notes,
        is_production_file="false",
        uploaded_by_id=user.id,
    )
    db.add(version)

    _log_activity(db, dr.id, user.id, "version_upload", f"Uploaded design version {max_version + 1}")
    db.commit()
    db.refresh(version)

    return {
        "id": version.id,
        "version_number": version.version_number,
        "file_path": version.file_path,
        "file_type": version.file_type,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.post("/design/requests/{request_id}/production-file")
async def designer_upload_production_file(
    request_id: str,
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """Upload a production file and mark request as completed."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    if dr.status != "production_needed":
        raise HTTPException(status_code=400, detail="Request is not in production_needed status")

    # Save file
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".dst"
    file_type = ext.lstrip(".")
    unique_name = generate_unique_filename(f"upload{ext}")
    contents = await file.read()
    relative_path = await save_file_bytes(contents, f"design_requests/production/{request_id}", unique_name, file.content_type or "application/octet-stream")

    version = DesignRequestVersion(
        design_request_id=request_id,
        version_number=0,  # Production files use 0 as marker
        file_path=relative_path,
        file_type=file_type,
        notes=notes,
        is_production_file="true",
        uploaded_by_id=user.id,
    )
    db.add(version)

    dr.status = "completed"
    dr.completed_at = datetime.utcnow()
    dr.updated_at = datetime.utcnow()

    _log_activity(db, dr.id, user.id, "production_file", "Production file uploaded, request completed")
    db.commit()
    db.refresh(dr)

    return _build_request_response(dr, db, include_internal=True)


@router.post("/design/requests/{request_id}/comments")
async def designer_add_comment(
    request_id: str,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """Add a comment to a design request."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    comment = DesignRequestComment(
        design_request_id=dr.id,
        user_id=user.id,
        message=data.message,
        attachment_path=data.attachment_path,
    )
    db.add(comment)
    _log_activity(db, dr.id, user.id, "comment", "Comment added by designer")
    db.commit()
    db.refresh(comment)

    return {"id": comment.id, "message": comment.message, "created_at": comment.created_at.isoformat()}


@router.post("/design/requests/upload")
async def designer_upload_file(
    file: UploadFile = File(...),
    user: StoreUser = Depends(require_store_role("designer", "design_manager", "admin")),
):
    """Upload a design file (general purpose)."""
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"
    unique_name = generate_unique_filename(f"upload{ext}")
    contents = await file.read()
    relative_path = await save_file_bytes(contents, "design_requests/files", unique_name, file.content_type or "application/octet-stream")
    return {"file_path": relative_path, "filename": file.filename}


# ===========================================================================
# ADMIN ENDPOINTS — /admin/design-requests/*
# ===========================================================================

@router.get("/admin/design-requests")
async def admin_list_design_requests(
    status: Optional[str] = Query(None),
    assigned_to_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("admin")),
):
    """List all design requests (admin view)."""
    query = db.query(DesignRequest)

    if status:
        query = query.filter(DesignRequest.status == status)
    if assigned_to_id:
        query = query.filter(DesignRequest.assigned_to_id == assigned_to_id)
    if priority:
        query = query.filter(DesignRequest.priority == priority)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            DesignRequest.request_number.ilike(term),
            DesignRequest.title.ilike(term),
            DesignRequest.customer_name.ilike(term),
        ))

    requests = query.order_by(desc(DesignRequest.created_at)).limit(limit).all()
    return [_build_request_list_item(dr, db) for dr in requests]


@router.get("/admin/design-requests/stats")
async def admin_design_request_stats(
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("admin")),
):
    """Queue stats for design requests."""
    total = db.query(func.count(DesignRequest.id)).scalar()
    submitted = db.query(func.count(DesignRequest.id)).filter(DesignRequest.status == "submitted").scalar()
    in_progress = db.query(func.count(DesignRequest.id)).filter(
        DesignRequest.status.in_(("assigned", "in_progress"))
    ).scalar()
    in_review = db.query(func.count(DesignRequest.id)).filter(DesignRequest.status == "review").scalar()
    overdue = db.query(func.count(DesignRequest.id)).filter(
        DesignRequest.due_date < datetime.utcnow(),
        DesignRequest.status.notin_(("completed", "rejected")),
    ).scalar()
    completed = db.query(func.count(DesignRequest.id)).filter(DesignRequest.status == "completed").scalar()

    # Get designers with their assignment counts
    designers = (
        db.query(StoreUser)
        .filter(StoreUser.role.in_(("designer", "admin")))
        .all()
    )
    designer_stats = []
    for d in designers:
        active_count = db.query(func.count(DesignRequest.id)).filter(
            DesignRequest.assigned_to_id == d.id,
            DesignRequest.status.notin_(("completed", "rejected")),
        ).scalar()
        designer_stats.append({
            "id": d.id,
            "name": f"{d.first_name} {d.last_name}".strip(),
            "active_requests": active_count,
        })

    return {
        "total": total,
        "submitted": submitted,
        "in_progress": in_progress,
        "in_review": in_review,
        "overdue": overdue,
        "completed": completed,
        "designers": designer_stats,
    }


@router.get("/admin/design-requests/{request_id}")
async def admin_get_design_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("admin")),
):
    """Get full detail for a design request (includes internal notes)."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    return _build_request_response(dr, db, include_internal=True)


@router.put("/admin/design-requests/{request_id}/assign")
async def admin_assign_design_request(
    request_id: str,
    data: AssignUpdate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("admin")),
):
    """Assign a design request to any designer."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    if data.assigned_to_id:
        assignee = db.query(StoreUser).filter(StoreUser.id == data.assigned_to_id).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")
        dr.assigned_to_id = data.assigned_to_id
        assignee_name = f"{assignee.first_name} {assignee.last_name}".strip()
    else:
        dr.assigned_to_id = None
        assignee_name = "Unassigned"

    if dr.status == "submitted" and dr.assigned_to_id:
        dr.status = "assigned"
    dr.updated_at = datetime.utcnow()

    _log_activity(db, dr.id, user.id, "assigned", f"Admin assigned to {assignee_name}")
    db.commit()
    db.refresh(dr)

    return _build_request_response(dr, db, include_internal=True)


@router.put("/admin/design-requests/{request_id}/status")
async def admin_override_status(
    request_id: str,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    user: StoreUser = Depends(require_store_role("admin")),
):
    """Admin override: set any valid status."""
    dr = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")

    old_status = dr.status
    dr.status = data.status
    dr.updated_at = datetime.utcnow()

    if data.status == "completed":
        dr.completed_at = datetime.utcnow()

    _log_activity(db, dr.id, user.id, "admin_override", f"Admin changed status: {old_status} → {data.status}")
    db.commit()
    db.refresh(dr)

    return _build_request_response(dr, db, include_internal=True)
