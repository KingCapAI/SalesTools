import os
import random
from datetime import date, datetime, timedelta

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import ics
from .availability import best_times, group_availability, slot_bounds
from .database import Base, engine, get_db
from .models import RSVP, BusyBlock, CalendarConnection, Event, Group, Membership, Message, User
from .suggestions import suggest

Base.metadata.create_all(bind=engine)

APP_URL = os.environ.get("HANGTIME_APP_URL", "http://localhost:5173")

app = FastAPI(title="Hangtime API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- auth helpers ----------

def _user_from_header(authorization: str | None, db: Session) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return db.query(User).filter(User.token == authorization.removeprefix("Bearer ").strip()).first()


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    user = _user_from_header(authorization, db)
    if not user:
        raise HTTPException(401, "Not signed in")
    return user


def optional_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    return _user_from_header(authorization, db)


def _membership(db: Session, user: User, group_id: int) -> Membership:
    m = db.query(Membership).filter_by(user_id=user.id, group_id=group_id).first()
    if not m:
        raise HTTPException(403, "You're not in this group")
    return m


# ---------- serializers ----------

def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "emoji": u.emoji, "city": u.city}


def group_out(g: Group, db: Session) -> dict:
    members = [user_out(m.user) for m in g.memberships]
    upcoming = (
        db.query(Event).filter(Event.group_id == g.id, Event.end >= datetime.now())
        .order_by(Event.start).all()
    )
    return {
        "id": g.id, "name": g.name, "emoji": g.emoji, "city": g.city,
        "invite_code": g.invite_code, "members": members,
        "upcoming_events": [event_out(e, db) for e in upcoming],
    }


def rsvp_out(r: RSVP, db: Session) -> dict:
    name, emoji = r.guest_name, "👋"
    if r.user_id:
        u = db.get(User, r.user_id)
        if u:
            name, emoji = u.name, u.emoji
    return {"user_id": r.user_id, "name": name or "Guest", "emoji": emoji, "status": r.status, "note": r.note}


def event_out(e: Event, db: Session) -> dict:
    creator = db.get(User, e.created_by)
    return {
        "id": e.id, "group_id": e.group_id, "title": e.title, "emoji": e.emoji,
        "description": e.description, "location_name": e.location_name, "address": e.address,
        "start": e.start.isoformat(), "end": e.end.isoformat(),
        "reminder_minutes": e.reminder_minutes, "share_code": e.share_code,
        "created_by": user_out(creator) if creator else None,
        "rsvps": [rsvp_out(r, db) for r in e.rsvps],
        "share_url": f"{APP_URL}/e/{e.share_code}",
    }


def message_out(m: Message, db: Session) -> dict:
    u = db.get(User, m.user_id)
    return {"id": m.id, "user": user_out(u) if u else None, "body": m.body,
            "created_at": m.created_at.isoformat()}


# ---------- auth ----------

class JoinIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    handle: str = Field(min_length=3, max_length=80)  # email or phone
    emoji: str = "😀"
    city: str = ""


@app.post("/api/auth/join")
def join(body: JoinIn, db: Session = Depends(get_db)):
    handle = body.handle.strip().lower()
    user = db.query(User).filter(User.handle == handle).first()
    if not user:
        user = User(name=body.name.strip(), handle=handle, emoji=body.emoji, city=body.city)
        db.add(user)
        db.commit()
        db.refresh(user)
    # Demo-grade auth: possession of the handle is trusted. Roadmap: SMS/email OTP.
    return {"token": user.token, "user": user_out(user)}


@app.get("/api/auth/demo-users")
def demo_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.handle.like("%@demo.hangtime")).all()
    return [{"handle": u.handle, **user_out(u)} for u in users]


@app.get("/api/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        **user_out(user),
        "handle": user.handle,
        "feed_url": f"/api/feed/{user.feed_token}.ics",
        "calendars": [
            {"id": c.id, "provider": c.provider, "label": c.label,
             "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None}
            for c in user.calendars
        ],
    }


# ---------- groups ----------

class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    emoji: str = "🎉"
    city: str = ""


@app.get("/api/groups")
def my_groups(user: User = Depends(current_user), db: Session = Depends(get_db)):
    groups = [m.group for m in db.query(Membership).filter_by(user_id=user.id).all()]
    return [group_out(g, db) for g in groups]


@app.post("/api/groups")
def create_group(body: GroupIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = Group(name=body.name.strip(), emoji=body.emoji, city=body.city, created_by=user.id)
    db.add(g)
    db.flush()
    db.add(Membership(user_id=user.id, group_id=g.id, role="owner"))
    db.commit()
    db.refresh(g)
    return group_out(g, db)


@app.get("/api/groups/{group_id}")
def get_group(group_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _membership(db, user, group_id)
    g = db.get(Group, group_id)
    if not g:
        raise HTTPException(404, "Group not found")
    out = group_out(g, db)
    out["invite_url"] = f"{APP_URL}/join/{g.invite_code}"
    return out


@app.get("/api/invites/{invite_code}")
def invite_preview(invite_code: str, db: Session = Depends(get_db)):
    g = db.query(Group).filter_by(invite_code=invite_code).first()
    if not g:
        raise HTTPException(404, "Invite not found")
    return {"name": g.name, "emoji": g.emoji, "city": g.city, "member_count": len(g.memberships)}


@app.post("/api/invites/{invite_code}/accept")
def accept_invite(invite_code: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.query(Group).filter_by(invite_code=invite_code).first()
    if not g:
        raise HTTPException(404, "Invite not found")
    if not db.query(Membership).filter_by(user_id=user.id, group_id=g.id).first():
        db.add(Membership(user_id=user.id, group_id=g.id))
        db.commit()
    return group_out(g, db)


@app.get("/api/groups/{group_id}/availability")
def availability(group_id: int, days: int = 14, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _membership(db, user, group_id)
    g = db.get(Group, group_id)
    member_ids = [m.user_id for m in g.memberships]
    grid = group_availability(db, member_ids, days=days)
    return {
        "members": {m.user_id: user_out(m.user) for m in g.memberships},
        "grid": grid,
        "best_times": best_times(grid, len(member_ids)),
    }


@app.get("/api/groups/{group_id}/suggestions")
def group_suggestions(group_id: int, slot: str | None = None, shuffle: int | None = None,
                      user: User = Depends(current_user), db: Session = Depends(get_db)):
    _membership(db, user, group_id)
    g = db.get(Group, group_id)
    return {"city": g.city, "ideas": suggest(g.city, slot=slot, seed=shuffle)}


# ---------- group + event chat ----------

class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


@app.get("/api/groups/{group_id}/messages")
def group_messages(group_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _membership(db, user, group_id)
    msgs = db.query(Message).filter_by(group_id=group_id).order_by(Message.created_at).limit(200).all()
    return [message_out(m, db) for m in msgs]


@app.post("/api/groups/{group_id}/messages")
def post_group_message(group_id: int, body: MessageIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _membership(db, user, group_id)
    m = Message(group_id=group_id, user_id=user.id, body=body.body.strip())
    db.add(m)
    db.commit()
    return message_out(m, db)


# ---------- events ----------

class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    emoji: str = "✨"
    description: str = ""
    location_name: str = ""
    address: str = ""
    date: str  # YYYY-MM-DD
    slot: str | None = None  # morning | afternoon | evening — or explicit times below
    start_time: str | None = None  # HH:MM
    end_time: str | None = None
    reminder_minutes: int = 60


@app.post("/api/groups/{group_id}/events")
def create_event(group_id: int, body: EventIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _membership(db, user, group_id)
    day = date.fromisoformat(body.date)
    if body.start_time:
        start = datetime.combine(day, datetime.strptime(body.start_time, "%H:%M").time())
        end = datetime.combine(day, datetime.strptime(body.end_time or body.start_time, "%H:%M").time())
        if end <= start:
            end = start + timedelta(hours=2)
    elif body.slot:
        start, end = slot_bounds(day, body.slot)
    else:
        raise HTTPException(422, "Pick a slot or a start time")

    e = Event(group_id=group_id, created_by=user.id, title=body.title.strip(), emoji=body.emoji,
              description=body.description, location_name=body.location_name, address=body.address,
              start=start, end=end, reminder_minutes=body.reminder_minutes)
    db.add(e)
    db.flush()
    db.add(RSVP(event_id=e.id, user_id=user.id, status="going"))
    db.commit()
    db.refresh(e)
    return event_out(e, db)


def _event_by_code(db: Session, share_code: str) -> Event:
    e = db.query(Event).filter_by(share_code=share_code).first()
    if not e:
        raise HTTPException(404, "Event not found")
    return e


@app.get("/api/events/{share_code}")
def get_event(share_code: str, user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    e = _event_by_code(db, share_code)
    out = event_out(e, db)
    out["group"] = {"id": e.group.id, "name": e.group.name, "emoji": e.group.emoji}
    out["is_member"] = bool(user and db.query(Membership).filter_by(user_id=user.id, group_id=e.group_id).first())
    my = user and next((r for r in e.rsvps if r.user_id == user.id), None)
    out["my_status"] = my.status if my else None
    return out


class RsvpIn(BaseModel):
    status: str = Field(pattern="^(going|maybe|cant)$")
    note: str = ""
    guest_name: str = ""


@app.post("/api/events/{share_code}/rsvp")
def rsvp(share_code: str, body: RsvpIn, user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    e = _event_by_code(db, share_code)
    if user:
        r = db.query(RSVP).filter_by(event_id=e.id, user_id=user.id).first()
        if not r:
            r = RSVP(event_id=e.id, user_id=user.id, status=body.status)
            db.add(r)
        r.status, r.note = body.status, body.note
    else:
        if not body.guest_name.strip():
            raise HTTPException(422, "Add your name so the group knows who's coming")
        r = db.query(RSVP).filter_by(event_id=e.id, user_id=None, guest_name=body.guest_name.strip()).first()
        if not r:
            r = RSVP(event_id=e.id, guest_name=body.guest_name.strip(), status=body.status)
            db.add(r)
        r.status, r.note = body.status, body.note
    # Going = this time is now busy for you across every group. One update, everywhere.
    if user and body.status == "going":
        exists = db.query(BusyBlock).filter_by(user_id=user.id, start=e.start, end=e.end).first()
        if not exists:
            db.add(BusyBlock(user_id=user.id, start=e.start, end=e.end))
    db.commit()
    return event_out(e, db)


@app.get("/api/events/{share_code}/messages")
def event_messages(share_code: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    e = _event_by_code(db, share_code)
    _membership(db, user, e.group_id)
    msgs = db.query(Message).filter_by(event_id=e.id).order_by(Message.created_at).limit(200).all()
    return [message_out(m, db) for m in msgs]


@app.post("/api/events/{share_code}/messages")
def post_event_message(share_code: str, body: MessageIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    e = _event_by_code(db, share_code)
    _membership(db, user, e.group_id)
    m = Message(event_id=e.id, user_id=user.id, body=body.body.strip())
    db.add(m)
    db.commit()
    return message_out(m, db)


@app.get("/api/events/{share_code}/ics")
def event_ics(share_code: str, db: Session = Depends(get_db)):
    e = _event_by_code(db, share_code)
    body = ics.event_to_ics(
        uid=e.share_code, title=f"{e.emoji} {e.title}", description=e.description,
        location=e.location_name + (f", {e.address}" if e.address else ""),
        start=e.start, end=e.end, url=f"{APP_URL}/e/{e.share_code}",
        reminder_minutes=e.reminder_minutes,
    )
    return Response(body, media_type="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="hangtime-{e.share_code}.ics"'})


# ---------- personal calendar sync ----------

@app.get("/api/feed/{feed_token}.ics")
def personal_feed(feed_token: str, db: Session = Depends(get_db)):
    """Subscribe-once feed: every hang you're going to (or invited to) lands in your
    own calendar app automatically. Works as a webcal:// URL in Apple/Google Calendar."""
    user = db.query(User).filter_by(feed_token=feed_token).first()
    if not user:
        raise HTTPException(404, "Feed not found")
    group_ids = [m.group_id for m in db.query(Membership).filter_by(user_id=user.id).all()]
    events = (
        db.query(Event)
        .filter(Event.group_id.in_(group_ids), Event.end >= datetime.now() - timedelta(days=7))
        .order_by(Event.start).all()
    )
    feed = ics.events_to_feed([
        {
            "uid": e.share_code, "title": f"{e.emoji} {e.title}", "description": e.description,
            "location": e.location_name + (f", {e.address}" if e.address else ""),
            "start": e.start, "end": e.end, "url": f"{APP_URL}/e/{e.share_code}",
            "reminder_minutes": e.reminder_minutes,
        }
        for e in events
    ])
    return Response(feed, media_type="text/calendar")


class CalendarIn(BaseModel):
    provider: str = Field(pattern="^(google|apple|ics|demo)$")
    label: str = "My calendar"
    ics_url: str = ""


def _seed_demo_busy(db: Session, user_id: int, connection_id: int, seed: int | None = None):
    rng = random.Random(seed if seed is not None else user_id * 7919)
    today = date.today()
    for i in range(14):
        day = today + timedelta(days=i)
        for slot_start, dur in [(9, 3), (13, 3), (18, 3)]:
            if rng.random() < (0.55 if day.weekday() < 5 and slot_start != 18 else 0.3):
                start = datetime.combine(day, datetime.min.time()) + timedelta(hours=slot_start)
                db.add(BusyBlock(user_id=user_id, connection_id=connection_id,
                                 start=start, end=start + timedelta(hours=dur)))


async def _sync_connection(db: Session, conn: CalendarConnection):
    db.query(BusyBlock).filter_by(connection_id=conn.id).delete()
    if conn.provider == "demo":
        _seed_demo_busy(db, conn.user_id, conn.id)
    elif conn.ics_url:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(conn.ics_url.replace("webcal://", "https://"))
            resp.raise_for_status()
        window_start = datetime.now() - timedelta(days=1)
        window_end = datetime.now() + timedelta(days=30)
        for start, end in ics.parse_busy_blocks(resp.text):
            if end > window_start and start < window_end:
                db.add(BusyBlock(user_id=conn.user_id, connection_id=conn.id, start=start, end=end))
    conn.last_synced_at = datetime.utcnow()
    db.commit()


@app.post("/api/me/calendars")
async def connect_calendar(body: CalendarIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.provider in ("google", "apple", "ics") and not body.ics_url.strip():
        raise HTTPException(422, "Paste your calendar's secret ICS address to connect it")
    conn = CalendarConnection(user_id=user.id, provider=body.provider,
                              label=body.label.strip() or "My calendar", ics_url=body.ics_url.strip())
    db.add(conn)
    db.commit()
    db.refresh(conn)
    try:
        await _sync_connection(db, conn)
    except httpx.HTTPError:
        db.delete(conn)
        db.commit()
        raise HTTPException(422, "Couldn't fetch that calendar URL — double-check the ICS link")
    return {"id": conn.id, "provider": conn.provider, "label": conn.label,
            "last_synced_at": conn.last_synced_at.isoformat() if conn.last_synced_at else None}


@app.post("/api/me/calendars/{conn_id}/sync")
async def resync_calendar(conn_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    conn = db.get(CalendarConnection, conn_id)
    if not conn or conn.user_id != user.id:
        raise HTTPException(404, "Calendar not found")
    try:
        await _sync_connection(db, conn)
    except httpx.HTTPError:
        raise HTTPException(422, "Couldn't reach that calendar right now")
    return {"ok": True, "last_synced_at": conn.last_synced_at.isoformat()}


@app.delete("/api/me/calendars/{conn_id}")
def disconnect_calendar(conn_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    conn = db.get(CalendarConnection, conn_id)
    if not conn or conn.user_id != user.id:
        raise HTTPException(404, "Calendar not found")
    db.query(BusyBlock).filter_by(connection_id=conn.id).delete()
    db.delete(conn)
    db.commit()
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True, "app": "hangtime"}


# ---------- production: serve the built frontend from the same service ----------

STATIC_DIR = os.environ.get(
    "HANGTIME_STATIC_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "frontend", "dist"),
)

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return FileResponse(os.path.join(STATIC_DIR, "manifest.webmanifest"), media_type="application/manifest+json")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
