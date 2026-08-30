# 🤙 Hangtime

**See when your friends are free. Plan the hang. Done.**

Work has a shared calendar. Family has a shared calendar. Friends have… a group chat
with 47 unanswered "we should hang soon" messages. Hangtime fixes that.

## The idea

- **Crews, not calendars.** Invite friends to a crew with a link you drop in the group
  text. No app download needed to RSVP — just like Partiful.
- **One calendar, everywhere.** Connect your Google/Apple calendar once. Hangtime reads
  *only free/busy time* (never event titles), so your crew sees *when* you're free, not
  *why* you're busy. Add a wedding to your work calendar and every crew instantly knows
  that Saturday is gone — no triple entry.
- **The heatmap.** A week-at-a-glance grid of the whole crew's availability. Greener =
  more friends free, 🔥 = everyone's free. Tap a slot → see who's in → plan it.
- **Best times & hang ideas.** Hangtime ranks the best upcoming slots (weights evenings
  and weekends) and suggests things to do based on the crew's city.
- **Plans that sync back.** Lock in a hang and it lands on everyone's own calendar:
  one-tap "Add to Google Calendar", .ics for Apple, or a subscribe-once personal feed
  (webcal) that keeps every future hang synced automatically — reminders included.
- **Texts are the front door.** Every event has a share link designed for iMessage:
  "🌮 Taco crawl — you in? RSVP here: …". Friends tap, RSVP as a guest in five seconds,
  and can join the crew after.
- **Built-in chat.** Per-crew and per-event threads for logistics, so plans don't get
  buried in the group text.

## Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite (`backend/`)
- **Frontend:** React 19 + Vite + TypeScript + Tailwind (`frontend/`) — mobile-first
  PWA, installable from the browser on iPhone/Android

## Run it

```bash
# Backend (port 8001)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed          # demo crew: 5 friends, busy calendars, a taco crawl
.venv/bin/uvicorn app.main:app --reload --port 8001

# Frontend (port 5173, proxies /api to 8001)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and tap one of the demo crew members to jump straight in.

## How calendar sync works today

- **In:** paste your calendar's secret ICS/webcal URL (Google, Apple/iCloud, Outlook —
  they all export one) and Hangtime pulls busy blocks for the next 30 days. A "demo
  calendar" provider generates realistic busy data for testing.
- **Out:** per-event .ics download (with a VALARM reminder), Google Calendar deep link,
  and a per-user private ICS feed you subscribe to once (`/api/feed/<token>.ics`) so
  every hang auto-appears in your own calendar app.
- RSVPing "going" also marks that slot busy across *all* your crews — one update,
  everywhere.

## Roadmap to production

1. **Real OAuth calendar sync** — Google Calendar API (freebusy endpoint) + Microsoft
   Graph, with background refresh instead of ICS polling; CalDAV for iCloud.
2. **Real auth** — SMS OTP (Twilio Verify) since phone numbers are the social graph.
3. **Native apps** — wrap the PWA with Capacitor for App Store/Play Store, push
   notifications for RSVPs, chat, and reminders.
4. **iMessage-native invites** — link previews (OpenGraph cards per event) and an
   iMessage app extension for inline RSVP.
5. **Smarter suggestions** — Google Places/Yelp keyed off the crew's real locations,
   ranked by the slot picked (brunch spots for mornings, bars for evenings).
6. **Availability polish** — timezone support, partial-day precision, "usually free"
   patterns learned per person.
