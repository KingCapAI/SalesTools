"""Minimal ICS (RFC 5545) helpers: parse busy blocks from a feed, generate event files.

Parsing intentionally only extracts DTSTART/DTEND pairs — Hangtime never stores
event titles or details from a connected calendar, only free/busy time.
"""
from datetime import datetime, timedelta

from dateutil import parser as dtparser


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _parse_dt(value: str, params: str) -> datetime | None:
    value = value.strip()
    try:
        if "VALUE=DATE" in params or (len(value) == 8 and value.isdigit()):
            return datetime.strptime(value, "%Y%m%d")
        dt = dtparser.parse(value)
        # Store naive local-ish time; drop tz for the demo's simple availability math.
        return dt.replace(tzinfo=None)
    except (ValueError, OverflowError):
        return None


def parse_busy_blocks(ics_text: str) -> list[tuple[datetime, datetime]]:
    blocks: list[tuple[datetime, datetime]] = []
    in_event = False
    start: datetime | None = None
    end: datetime | None = None
    for line in _unfold(ics_text):
        upper = line.upper()
        if upper.startswith("BEGIN:VEVENT"):
            in_event, start, end = True, None, None
        elif upper.startswith("END:VEVENT"):
            if in_event and start:
                blocks.append((start, end or start + timedelta(hours=1)))
            in_event = False
        elif in_event and ":" in line:
            prop, value = line.split(":", 1)
            name = prop.split(";")[0].upper()
            if name == "DTSTART":
                start = _parse_dt(value, prop.upper())
            elif name == "DTEND":
                end = _parse_dt(value, prop.upper())
    return blocks


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def event_to_ics(*, uid: str, title: str, description: str, location: str,
                 start: datetime, end: datetime, url: str, reminder_minutes: int) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Hangtime//EN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}@hangtime.app",
        f"DTSTAMP:{_fmt(datetime.utcnow())}",
        f"DTSTART:{_fmt(start)}",
        f"DTEND:{_fmt(end)}",
        f"SUMMARY:{_escape(title)}",
        f"DESCRIPTION:{_escape(description + (chr(10) + url if url else ''))}",
        f"LOCATION:{_escape(location)}",
        f"URL:{url}",
    ]
    if reminder_minutes > 0:
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_escape(title)}",
            f"TRIGGER:-PT{reminder_minutes}M",
            "END:VALARM",
        ]
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


def events_to_feed(events: list[dict]) -> str:
    """events: list of dicts with uid, title, description, location, start, end, url, reminder_minutes."""
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Hangtime//EN", "X-WR-CALNAME:Hangtime"]
    for ev in events:
        body = event_to_ics(**ev)
        chunk = body.split("BEGIN:VEVENT", 1)[1].rsplit("END:VEVENT", 1)[0]
        out += ["BEGIN:VEVENT" + chunk.rstrip() ,"END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"
