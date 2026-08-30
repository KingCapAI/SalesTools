import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, post, type Me } from '../api'
import { useAuth } from '../App'

const EMOJIS = ['🧢', '🌸', '🏀', '🎸', '🎨', '🦖', '🍕', '🛹', '🌈', '👾', '🐸', '🥑']

type DemoUser = { handle: string; id: number; name: string; emoji: string; city: string }

export default function Welcome() {
  const { user, signIn } = useAuth()
  const nav = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next') || '/home'

  const [name, setName] = useState('')
  const [handle, setHandle] = useState('')
  const [emoji, setEmoji] = useState('🧢')
  const [city, setCity] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>([])

  useEffect(() => {
    if (user) nav(next, { replace: true })
  }, [user, nav, next])

  useEffect(() => {
    get<DemoUser[]>('/api/auth/demo-users').then(setDemoUsers).catch(() => {})
  }, [])

  const join = async (n: string, h: string, e: string, c: string) => {
    setBusy(true)
    setError('')
    try {
      const res = await post<{ token: string; user: Me }>('/api/auth/join', {
        name: n, handle: h, emoji: e, city: c,
      })
      signIn(res.token, res.user)
      nav(next, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-xl flex-col justify-center px-5 py-10">
      <div className="mb-8 text-center">
        <div className="text-7xl">🤙</div>
        <h1 className="mt-2 text-5xl font-black tracking-tight">Hangtime</h1>
        <p className="mt-3 text-lg font-bold text-ink/70">
          See when your friends are free.
          <br />
          Plan the hang. Done.
        </p>
      </div>

      <form
        className="card space-y-3 p-5"
        onSubmit={(e) => {
          e.preventDefault()
          if (name.trim() && handle.trim()) join(name, handle, emoji, city)
        }}
      >
        <input className="input" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
        <input
          className="input"
          placeholder="Phone or email"
          value={handle}
          onChange={(e) => setHandle(e.target.value)}
        />
        <input
          className="input"
          placeholder="Your city (for hang ideas) — optional"
          value={city}
          onChange={(e) => setCity(e.target.value)}
        />
        <div className="flex flex-wrap gap-1.5">
          {EMOJIS.map((e) => (
            <button
              type="button"
              key={e}
              onClick={() => setEmoji(e)}
              className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-xl transition ${
                emoji === e ? 'border-ink bg-pop-sunshine shadow-poplite' : 'border-ink/15 bg-white'
              }`}
            >
              {e}
            </button>
          ))}
        </div>
        {error && <p className="font-bold text-pop-coral">{error}</p>}
        <button className="btn-primary w-full text-lg" disabled={busy || !name.trim() || !handle.trim()}>
          {busy ? 'One sec…' : "Let's go →"}
        </button>
      </form>

      {demoUsers.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-center text-sm font-black uppercase tracking-wide text-ink/50">
            or hop into the demo crew
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {demoUsers.map((d) => (
              <button
                key={d.handle}
                className="chip bg-white shadow-poplite active:translate-y-[2px] active:shadow-none"
                onClick={() => join(d.name, d.handle, d.emoji, d.city)}
              >
                {d.emoji} {d.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
