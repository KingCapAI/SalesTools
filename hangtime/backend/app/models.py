import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def gen_code(n: int = 8) -> str:
    return secrets.token_urlsafe(n)[:n].replace("-", "x").replace("_", "y")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    handle: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # email or phone
    emoji: Mapped[str] = mapped_column(String(8), default="😀")
    city: Mapped[str] = mapped_column(String(80), default="")
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(32))
    feed_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")
    calendars: Mapped[list["CalendarConnection"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20))  # google | apple | ics | demo
    label: Mapped[str] = mapped_column(String(120), default="My calendar")
    ics_url: Mapped[str] = mapped_column(Text, default="")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="calendars")


class BusyBlock(Base):
    __tablename__ = "busy_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    connection_id: Mapped[int | None] = mapped_column(ForeignKey("calendar_connections.id"), nullable=True)
    start: Mapped[datetime] = mapped_column(DateTime, index=True)
    end: Mapped[datetime] = mapped_column(DateTime)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    emoji: Mapped[str] = mapped_column(String(8), default="🎉")
    city: Mapped[str] = mapped_column(String(80), default="")
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=gen_code)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="group")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # owner | member
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="memberships")
    group: Mapped[Group] = relationship(back_populates="memberships")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(140))
    emoji: Mapped[str] = mapped_column(String(8), default="✨")
    description: Mapped[str] = mapped_column(Text, default="")
    location_name: Mapped[str] = mapped_column(String(140), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    start: Mapped[datetime] = mapped_column(DateTime, index=True)
    end: Mapped[datetime] = mapped_column(DateTime)
    reminder_minutes: Mapped[int] = mapped_column(Integer, default=60)
    share_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=gen_code)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    group: Mapped[Group] = relationship(back_populates="events")
    rsvps: Mapped[list["RSVP"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class RSVP(Base):
    __tablename__ = "rsvps"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    guest_name: Mapped[str] = mapped_column(String(80), default="")  # for link RSVPs without an account
    status: Mapped[str] = mapped_column(String(10))  # going | maybe | cant
    note: Mapped[str] = mapped_column(String(200), default="")
    synced_to_calendar: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event: Mapped["Event"] = relationship(back_populates="rsvps")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True, index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped["Event"] = relationship(back_populates="messages")
