import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { get } from '../api'
import AvatarStack from '../components/AvatarStack'
import Shell from '../components/Shell'
import type { EventOut, GroupOut } from '../types'
import { formatWhen } from '../util'

export default function Home() {
  const [groups, setGroups] = useState<GroupOut[] | null>(null)

  useEffect(() => {
    get<GroupOut[]>('/api/groups').then(setGroups).catch(() => setGroups([]))
  }, [])

  const upcoming: EventOut[] = (groups ?? [])
    .flatMap((g) => g.upcoming_events.map((e) => ({ ...e, group: { id: g.id, name: g.name, emoji: g.emoji } })))
    .sort((a, b) => a.start.localeCompare(b.start))
    .slice(0, 5)

  return (
    <Shell>
      {upcoming.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 text-xl font-black">Coming up</h2>
          <div className="space-y-3">
            {upcoming.map((e) => (
              <Link key={e.id} to={`/e/${e.share_code}`} className="card block p-4">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{e.emoji}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-black">{e.title}</p>
                    <p className="text-sm font-bold text-ink/60">
                      {formatWhen(e.start)} · {e.group?.emoji} {e.group?.name}
                    </p>
                  </div>
                  <span className="chip bg-pop-mint/40">
                    {e.rsvps.filter((r) => r.status === 'going').length} going
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xl font-black">Your crews</h2>
        <Link to="/groups/new" className="chip bg-pop-coral text-white shadow-poplite">
          + new crew
        </Link>
      </div>

      {groups === null ? (
        <p className="font-bold text-ink/50">Loading…</p>
      ) : groups.length === 0 ? (
        <div className="card p-6 text-center">
          <p className="text-4xl">🫂</p>
          <p className="mt-2 font-black">No crews yet</p>
          <p className="mt-1 font-bold text-ink/60">
            Start one and text your friends the invite link — that's the whole onboarding.
          </p>
          <Link to="/groups/new" className="btn-primary mt-4">
            Start a crew
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((g) => (
            <Link key={g.id} to={`/g/${g.id}`} className="card block p-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{g.emoji}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-lg font-black">{g.name}</p>
                  <p className="text-sm font-bold text-ink/60">
                    {g.members.length} friends{g.city ? ` · ${g.city}` : ''}
                  </p>
                </div>
                <AvatarStack users={g.members} max={4} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </Shell>
  )
}
