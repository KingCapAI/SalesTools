"""Seed the demo world: five friends, one group, busy calendars, an upcoming hang.

Run once:  python -m app.seed
"""
from datetime import date, datetime, time, timedelta

from .database import Base, SessionLocal, engine
from .main import _seed_demo_busy  # reuse the demo busy-block generator
from .models import RSVP, CalendarConnection, Event, Group, Membership, Message, User

DEMO_PEOPLE = [
    ("Eric", "eric@demo.hangtime", "🧢", "Los Angeles"),
    ("Maya", "maya@demo.hangtime", "🌸", "Los Angeles"),
    ("Jordan", "jordan@demo.hangtime", "🏀", "Los Angeles"),
    ("Sam", "sam@demo.hangtime", "🎸", "Los Angeles"),
    ("Priya", "priya@demo.hangtime", "🎨", "Los Angeles"),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.handle == DEMO_PEOPLE[0][1]).first():
            print("Demo data already seeded — nothing to do.")
            return

        users = []
        for i, (name, handle, emoji, city) in enumerate(DEMO_PEOPLE):
            u = User(name=name, handle=handle, emoji=emoji, city=city)
            db.add(u)
            db.flush()
            conn = CalendarConnection(user_id=u.id, provider="demo", label=f"{name}'s calendar",
                                      last_synced_at=datetime.utcnow())
            db.add(conn)
            db.flush()
            _seed_demo_busy(db, u.id, conn.id, seed=1000 + i)
            users.append(u)

        group = Group(name="The Crew", emoji="🍻", city="Los Angeles", created_by=users[0].id)
        db.add(group)
        db.flush()
        for i, u in enumerate(users):
            db.add(Membership(user_id=u.id, group_id=group.id, role="owner" if i == 0 else "member"))

        # An upcoming hang this Saturday evening
        today = date.today()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
        ev = Event(group_id=group.id, created_by=users[0].id, title="Taco crawl", emoji="🌮",
                   description="Three spots, one champion. Bring cash for the last stand.",
                   location_name="Sonoratown", address="208 E 8th St, Los Angeles",
                   start=datetime.combine(saturday, time(18, 0)),
                   end=datetime.combine(saturday, time(21, 0)))
        db.add(ev)
        db.flush()
        for u, status in zip(users, ["going", "going", "maybe", "going", "cant"]):
            db.add(RSVP(event_id=ev.id, user_id=u.id, status=status,
                        note="babysitter fell through 😭" if status == "cant" else ""))

        for u, body in [
            (users[0], "ok taco crawl saturday, who's in 🌮"),
            (users[1], "SO in. starting at sonoratown right?"),
            (users[3], "i'll drive if someone buys my horchata"),
            (users[2], "70% in, waiting on my boss to confirm i'm free"),
        ]:
            db.add(Message(event_id=ev.id, user_id=u.id, body=body))

        db.add(Message(group_id=group.id, user_id=users[4].id,
                       body="we should do a beach day before summer ends btw"))
        db.add(Message(group_id=group.id, user_id=users[1].id, body="heatmap says sunday afternoon 👀"))

        db.commit()
        print(f"Seeded {len(users)} friends, group '{group.name}' (invite {group.invite_code}), "
              f"event '{ev.title}' ({ev.share_code}).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
