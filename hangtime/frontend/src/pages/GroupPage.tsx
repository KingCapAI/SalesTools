import clsx from 'clsx'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { get, post } from '../api'
import { useAuth } from '../App'
import AvatarStack from '../components/AvatarStack'
import Heatmap, { type CellPick } from '../components/Heatmap'
import Shell from '../components/Shell'
import type { Availability, ChatMessage, GroupOut, Idea } from '../types'
import { copyText, formatDay, formatWhen, shareEvent, SLOT_LABELS } from '../util'

type Tab = 'times' | 'hangs' | 'chat' | 'crew'

export default function GroupPage() {
  const { groupId } = useParams()
  const nav = useNavigate()
  const { user } = useAuth()
  const [group, setGroup] = useState<GroupOut | null>(null)
  const [avail, setAvail] = useState<Availability | null>(null)
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [tab, setTab] = useState<Tab>('times')
  const [picked, setPicked] = useState<CellPick | null>(null)
  const [copied, setCopied] = useState(false)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')

  const loadIdeas = useCallback(
    (slot?: string) => {
      get<{ ideas: Idea[] }>(
        `/api/groups/${groupId}/suggestions?shuffle=${Math.floor(Math.random() * 1e6)}${slot ? `&slot=${slot}` : ''}`,
      )
        .then((r) => setIdeas(r.ideas))
        .catch(() => {})
    },
    [groupId],
  )

  useEffect(() => {
    get<GroupOut>(`/api/groups/${groupId}`).then(setGroup).catch(() => nav('/home'))
    get<Availability>(`/api/groups/${groupId}/availability`).then(setAvail).catch(() => {})
    loadIdeas()
  }, [groupId, nav, loadIdeas])

  useEffect(() => {
    if (tab !== 'chat') return
    get<ChatMessage[]>(`/api/groups/${groupId}/messages`).then(setMessages).catch(() => {})
  }, [tab, groupId])

  const send = async () => {
    if (!draft.trim()) return
    const m = await post<ChatMessage>(`/api/groups/${groupId}/messages`, { body: draft })
    setMessages((prev) => [...prev, m])
    setDraft('')
  }

  const planUrl = (date?: string, slot?: string, ideaTitle?: string, ideaEmoji?: string) => {
    const q = new URLSearchParams()
    if (date) q.set('date', date)
    if (slot) q.set('slot', slot)
    if (ideaTitle) q.set('title', ideaTitle)
    if (ideaEmoji) q.set('emoji', ideaEmoji)
    return `/g/${groupId}/new?${q.toString()}`
  }

  if (!group) return <Shell back="/home"><p className="font-bold text-ink/50">Loading…</p></Shell>

  const memberCount = group.members.length
  const inviteUrl = `${window.location.origin}/join/${group.invite_code}`

  return (
    <Shell back="/home">
      <div className="mb-4 flex items-center gap-3">
        <span className="text-4xl">{group.emoji}</span>
        <div className="flex-1">
          <h1 className="text-2xl font-black leading-tight">{group.name}</h1>
          <p className="text-sm font-bold text-ink/60">
            {memberCount} friends{group.city ? ` · ${group.city}` : ''}
          </p>
        </div>
        <AvatarStack users={group.members} max={3} />
      </div>

      <div className="mb-4 flex gap-2 overflow-x-auto">
        {(
          [
            ['times', '🗓️ Free times'],
            ['hangs', '✨ Hangs'],
            ['chat', '💬 Chat'],
            ['crew', '🫂 Crew'],
          ] as [Tab, string][]
        ).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx('chip whitespace-nowrap', tab === t ? 'bg-ink text-white' : 'bg-white')}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'times' && (
        <div className="space-y-4">
          {avail && avail.best_times.length > 0 && (
            <div>
              <h2 className="mb-2 font-black">🏆 Best times to hang</h2>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {avail.best_times.map((bt) => (
                  <Link
                    key={`${bt.date}-${bt.slot}`}
                    to={planUrl(bt.date, bt.slot)}
                    className="chip whitespace-nowrap bg-pop-mint/50 shadow-poplite"
                  >
                    {formatDay(bt.date)} {bt.slot === 'evening' ? '🌙' : bt.slot === 'morning' ? '☀️' : '🌤️'}{' '}
                    {bt.free_count}/{memberCount} free
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="card p-4">
            {avail ? <Heatmap availability={avail} onPick={setPicked} /> : <p className="font-bold text-ink/50">Crunching calendars…</p>}
          </div>

          {picked && avail && (
            <div className="card border-pop-sky bg-pop-sky/10 p-4">
              <p className="font-black">
                {formatDay(picked.date)} · {SLOT_LABELS[picked.slot]}
              </p>
              <p className="mt-1 text-sm font-bold text-ink/70">
                {picked.free_ids.length === 0
                  ? 'Nobody’s free — cursed slot 💀'
                  : `Free: ${picked.free_ids.map((id) => `${avail.members[id]?.emoji ?? ''} ${avail.members[id]?.name ?? ''}`).join(', ')}`}
              </p>
              {picked.free_ids.length > 0 && (
                <Link to={planUrl(picked.date, picked.slot)} className="btn-primary mt-3">
                  Plan something here →
                </Link>
              )}
            </div>
          )}

          <div>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-black">💡 Hang ideas{group.city ? ` · ${group.city}` : ''}</h2>
              <button className="chip bg-white" onClick={() => loadIdeas(picked?.slot)}>
                🎲 shuffle
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {ideas.map((idea) => (
                <Link
                  key={idea.title}
                  to={planUrl(picked?.date, picked?.slot ?? idea.slot, idea.title, idea.emoji)}
                  className="card p-3"
                >
                  <p className="text-2xl">{idea.emoji}</p>
                  <p className="mt-1 font-black leading-tight">{idea.title}</p>
                  <p className="mt-1 text-xs font-bold text-ink/60">{idea.blurb}</p>
                  <p className="mt-1 text-xs font-black text-ink/40">{idea.cost} · {idea.vibe}</p>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'hangs' && (
        <div className="space-y-3">
          <Link to={planUrl()} className="btn-primary w-full">
            + Plan a hang
          </Link>
          {group.upcoming_events.length === 0 && (
            <div className="card p-6 text-center font-bold text-ink/60">
              Nothing on the books. Check the free times tab and fix that 👀
            </div>
          )}
          {group.upcoming_events.map((e) => (
            <Link key={e.id} to={`/e/${e.share_code}`} className="card block p-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{e.emoji}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-black">{e.title}</p>
                  <p className="text-sm font-bold text-ink/60">
                    {formatWhen(e.start)}
                    {e.location_name ? ` · ${e.location_name}` : ''}
                  </p>
                </div>
                <span className="chip bg-pop-mint/40">{e.rsvps.filter((r) => r.status === 'going').length} going</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {tab === 'chat' && (
        <div className="flex flex-col">
          <div className="card mb-3 max-h-[24rem] space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && <p className="text-center font-bold text-ink/50">Say something first, coward 💬</p>}
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
              placeholder="Message the crew…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
            />
            <button className="btn-primary" onClick={send} disabled={!draft.trim()}>
              Send
            </button>
          </div>
        </div>
      )}

      {tab === 'crew' && (
        <div className="space-y-4">
          <div className="card p-4">
            <h2 className="font-black">📲 Invite friends</h2>
            <p className="mt-1 text-sm font-bold text-ink/60">
              Text them this link — they tap it, pick an emoji, and they're in.
            </p>
            <div className="mt-3 flex gap-2">
              <button
                className="btn-primary flex-1"
                onClick={() => shareEvent(`Join "${group.name}" on Hangtime`, inviteUrl)}
              >
                💬 Text the link
              </button>
              <button
                className="btn-secondary"
                onClick={async () => {
                  if (await copyText(inviteUrl)) {
                    setCopied(true)
                    setTimeout(() => setCopied(false), 1500)
                  }
                }}
              >
                {copied ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <div className="card divide-y-2 divide-ink/10 p-2">
            {group.members.map((m) => (
              <div key={m.id} className="flex items-center gap-3 p-3">
                <span className="text-2xl">{m.emoji}</span>
                <p className="font-black">{m.name}</p>
                {m.id === user?.id && <span className="chip bg-pop-sunshine/70 text-xs">you</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </Shell>
  )
}
