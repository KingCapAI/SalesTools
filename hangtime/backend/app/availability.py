from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .models import BusyBlock

SLOTS = [
    ("morning", time(9, 0), time(12, 0)),
    ("afternoon", time(12, 0), time(17, 0)),
    ("evening", time(17, 0), time(22, 0)),
]

SLOT_TIMES = {name: (start, end) for name, start, end in SLOTS}


def slot_bounds(day: date, slot: str) -> tuple[datetime, datetime]:
    start_t, end_t = SLOT_TIMES[slot]
    return datetime.combine(day, start_t), datetime.combine(day, end_t)


def group_availability(db: Session, member_ids: list[int], days: int = 14) -> list[dict]:
    """Grid of the next `days` days x 3 slots -> which members are free."""
    today = date.today()
    window_start = datetime.combine(today, time.min)
    window_end = window_start + timedelta(days=days)

    blocks = (
        db.query(BusyBlock)
        .filter(BusyBlock.user_id.in_(member_ids), BusyBlock.end > window_start, BusyBlock.start < window_end)
        .all()
    )
    by_user: dict[int, list[BusyBlock]] = {uid: [] for uid in member_ids}
    for b in blocks:
        by_user.setdefault(b.user_id, []).append(b)

    grid = []
    for i in range(days):
        day = today + timedelta(days=i)
        day_slots = []
        for slot_name, _, _ in SLOTS:
            s, e = slot_bounds(day, slot_name)
            free = [
                uid for uid in member_ids
                if not any(b.start < e and b.end > s for b in by_user.get(uid, []))
            ]
            day_slots.append({"slot": slot_name, "free_ids": free, "free_count": len(free)})
        grid.append({
            "date": day.isoformat(),
            "weekday": day.strftime("%a"),
            "is_weekend": day.weekday() >= 5,
            "slots": day_slots,
        })
    return grid


def best_times(grid: list[dict], member_count: int, limit: int = 4) -> list[dict]:
    """Rank slots: most people free wins; weekend + evening break ties; sooner beats later."""
    scored = []
    for di, day in enumerate(grid):
        for slot in day["slots"]:
            if slot["free_count"] < max(2, (member_count + 1) // 2):
                continue
            score = slot["free_count"] * 100
            if day["is_weekend"]:
                score += 20
            if slot["slot"] == "evening":
                score += 10
            score -= di  # prefer sooner
            scored.append({"date": day["date"], "weekday": day["weekday"], "slot": slot["slot"],
                           "free_ids": slot["free_ids"], "free_count": slot["free_count"], "score": score})
    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]
