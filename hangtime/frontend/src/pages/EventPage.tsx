import clsx from 'clsx'
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { get, post } from '../api'
import { useAuth } from '../App'
import Shell from '../components/Shell'
import type { ChatMessage, EventOut, Rsvp } from '../types'
import { formatWhen, shareEvent } from '../util'

const STATUS_META: Record<Rsvp['status'], { label: string; cls: string }> = {
  going: { label: "🎉 I'm in", cls: 'bg-pop-mint/60' },
  maybe: { label: '🤔 Maybe', cls: 'bg-pop-sunshine/60' },
  cant: { label: "😭 Can't", cls: 'bg-white' },
}

function gcalUrl(e: EventOut): string {
  const fmt = (iso: string) => iso.replace(/[-:]/g, '').slice(0, 15)
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: `${e.emoji} ${e.title}`,
    dates: `${fmt(e.start)}/${fmt(e.end)}`,
    details: `${e.description}\n\n${e.share_url}`.trim(),
    location: [e.location_name, e.address].filter(Boolean).join(', '),
  })
  return `https://calendar.google.com/calendar/render?${params.toString()}`
}

export default function EventPage() {
  const { shareCode } = useParams()
  const [params] = useSearchParams()
  const { user } = useAuth()
  const [event, setEvent] = useState<EventOut | null>(null)
  const [guestName, setGuestName] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [justCreated] = useState(params.get('created') === '1')

  const load = useCallback(() => {
    get<EventOut>(`/api/events/${shareCode}`).then(setEvent).catch(() => {})
  }, [shareCode])

  useEffect(load, [load])

  useEffect(() => {
    if (event?.is_member) {
      get<ChatMessage[]>(`/api/events/${shareCode}/messages`).then(setMessages).catch(() => {})
    }
  }, [event?.is_member, shareCode])

  const rsvp = async (status: Rsvp['status']) => {
    if (!user && !guestName.trim()) return
    const updated = await post<EventOut>(`/api/events/${shareCode}/rsvp`, {
      status,
      guest_name: user ? '' : guestName.trim(),
    })
    setEvent((prev) => (prev ? { ...prev, ...updated, my_status: user ? status : prev.my_status } : prev))
  }

  const send = async () => {
    if (!draft.trim()) return
    const m = await post<ChatMessage>(`/api/events/${shareCode}/messages`, { body: draft })
    setMessages((prev) => [...prev, m])
    setDraft('')
  }

  if (!event) {
    return (
      <Shell>
        <p className="font-bold text-ink/50">Loading the hang…</p>
      </Shell>
    )
  }

  const going = event.rsvps.filter((r) => r.status === 'going')
  const maybe = event.rsvps.filter((r) => r.status === 'maybe')
  const cant = event.rsvps.filter((r) => r.status === 'cant')

  return (
    <Shell back={event.is_member ? `/g/${event.group_id}` : undefined}>
      {justCreated && (
        <div className="card mb-4 border-pop-mint bg-pop-mint/20 p-4 text-center font-black">
          🎊 Locked in! Now text the crew the link so nobody has an excuse.
        </div>
      )}

      <div className="card p-5 text-center">
        <div className="text-6xl">{event.emoji}</div>
        <h1 className="mt-2 text-3xl font-black leading-tight">{event.title}</h1>
        <p className="mt-2 text-lg font-bold text-ink/70">{formatWhen(event.start)}</p>
        {event.location_name && (
          <p className="font-bold text-ink/60">
            📍 {event.location_name}
            {event.address ? ` · ${event.address}` : ''}
          </p>
        )}
        {event.group && (
          <p className="mt-1 text-sm font-bold text-ink/50">
            with {event.group.emoji} {event.group.name}
          </p>
        )}
        {event.description && <p className="mt-3 font-semibold text-ink/80">{event.description}</p>}

        {!user && (
          <input
            className="input mt-4"
            placeholder="Your name (so the crew knows it's you)"
            value={guestName}
            onChange={(e) => setGuestName(e.target.value)}
          />
        )}
        <div className="mt-4 grid grid-cols-3 gap-2">
          {(Object.keys(STATUS_META) as Rsvp['status'][]).map((s) => (
            <button
              key={s}
              onClick={() => rsvp(s)}
              className={clsx(
                'btn justify-center px-2 text-sm',
                STATUS_META[s].cls,
                event.my_status === s && 'ring-4 ring-pop-sky/60',
              )}
            >
              {STATUS_META[s].label}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <button className="btn-secondary text-sm" onClick={() => shareEvent(`${event.emoji} ${event.title}`, `${window.location.origin}/e/${event.share_code}`)}>
            💬 Text the invite
          </button>
          <a className="btn-secondary text-sm" href={`/api/events/${event.share_code}/ics`}>
            📅 Apple / .ics
          </a>
          <a className="btn-secondary text-sm" href={gcalUrl(event)} target="_blank" rel="noreferrer">
            📆 Google Cal
          </a>
        </div>
        <p className="mt-2 text-xs font-bold text-ink/40">
          ⏰ reminder set for {event.reminder_minutes >= 1440 ? 'a day' : `${event.reminder_minutes} min`} before
        </p>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-center">
        {[
          ['Going', going, 'bg-pop-mint/30'],
          ['Maybe', maybe, 'bg-pop-sunshine/30'],
          ["Can't", cant, 'bg-white'],
        ].map(([label, list, cls]) => (
          <div key={label as string} className={clsx('card p-3', cls as string)}>
            <p className="font-black">
              {label as string} · {(list as Rsvp[]).length}
            </p>
            <div className="mt-2 space-y-1">
              {(list as Rsvp[]).map((r, i) => (
                <p key={i} className="truncate text-sm font-bold" title={r.note}>
                  {r.emoji} {r.name}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>

      {event.is_member ? (
        <div className="mt-4">
          <h2 className="mb-2 font-black">💬 The thread</h2>
          <div className="card mb-3 max-h-72 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && <p className="text-center font-bold text-ink/50">No messages yet</p>}
            {messages.map((m) => (
              <div key={m.id} className={clsx('flex gap-2', m.user?.id === user?.id && 'flex-row-reverse')}>
                <span className="text-xl">{m.user?.emoji}</span>
                <div
                  className={clsx(
                    'max-w-[75%] rounded-2xl border-2 border-ink px-3 py-2',
                    m.user?.id === user?.id ? 'bg-pop-sunshine/70' : 'bg-white',
                  )}
                >
                  <p className="text-xs font-black text-ink/50">{m.user?.name}</p>
                  <p className="font-bold">{m.body}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              className="input flex-1"
              placeholder="Talk logistics…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
            />
            <button className="btn-primary" onClick={send} disabled={!draft.trim()}>
              Send
            </button>
          </div>
        </div>
      ) : (
        !user && (
          <div className="card mt-4 p-4 text-center">
            <p className="font-black">Want the full experience?</p>
            <p className="mt-1 text-sm font-bold text-ink/60">
              Join Hangtime to see when this crew is free, chat, and get it on your calendar automatically.
            </p>
            <Link to={`/?next=/e/${event.share_code}`} className="btn-primary mt-3">
              Join free →
            </Link>
          </div>
        )
      )}
    </Shell>
  )
}
