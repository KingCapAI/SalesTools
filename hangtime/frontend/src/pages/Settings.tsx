import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { del, get, post } from '../api'
import { useAuth } from '../App'
import Shell from '../components/Shell'
import type { MeFull } from '../types'
import { copyText } from '../util'

const PROVIDERS = [
  { value: 'google', label: '📆 Google Calendar', hint: 'Google Calendar → Settings → your calendar → "Secret address in iCal format"' },
  { value: 'apple', label: '🍎 Apple / iCloud', hint: 'icloud.com → Calendar → share icon → Public Calendar → copy the webcal link' },
  { value: 'ics', label: '🔗 Any ICS link', hint: 'Outlook, Fastmail, anything that exports an .ics feed URL' },
  { value: 'demo', label: '🎲 Demo calendar', hint: 'Fills your next two weeks with realistic fake busy blocks' },
] as const

export default function Settings() {
  const { user, signOut } = useAuth()
  const nav = useNavigate()
  const [me, setMe] = useState<MeFull | null>(null)
  const [provider, setProvider] = useState<(typeof PROVIDERS)[number]['value']>('google')
  const [icsUrl, setIcsUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  const load = useCallback(() => {
    get<MeFull>('/api/me').then(setMe).catch(() => {})
  }, [])
  useEffect(load, [load])

  const connect = async () => {
    setBusy(true)
    setError('')
    try {
      await post('/api/me/calendars', {
        provider,
        label: PROVIDERS.find((p) => p.value === provider)?.label ?? 'My calendar',
        ics_url: provider === 'demo' ? '' : icsUrl,
      })
      setIcsUrl('')
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not connect')
    } finally {
      setBusy(false)
    }
  }

  const feedUrl = me ? `${window.location.origin}${me.feed_url}` : ''
  const hint = PROVIDERS.find((p) => p.value === provider)?.hint

  return (
    <Shell back="/home">
      <h1 className="mb-1 text-3xl font-black">
        {user?.emoji} {user?.name}
      </h1>
      <p className="mb-5 font-bold text-ink/60">{me?.handle}</p>

      <section className="card mb-4 p-5">
        <h2 className="font-black">🔌 Your calendars</h2>
        <p className="mt-1 text-sm font-bold text-ink/60">
          Connect them so your crews see when you're free. Hangtime only reads busy times — never event titles or details.
        </p>

        {me && me.calendars.length > 0 && (
          <div className="mt-3 space-y-2">
            {me.calendars.map((c) => (
              <div key={c.id} className="flex items-center justify-between rounded-2xl border-2 border-ink/15 px-3 py-2">
                <div>
                  <p className="font-black">{c.label}</p>
                  <p className="text-xs font-bold text-ink/50">
                    {c.last_synced_at ? `synced ${new Date(c.last_synced_at + 'Z').toLocaleString()}` : 'not synced yet'}
                  </p>
                </div>
                <div className="flex gap-1">
                  <button className="chip bg-white text-xs" onClick={() => post(`/api/me/calendars/${c.id}/sync`).then(load)}>
                    ↻ sync
                  </button>
                  <button className="chip bg-white text-xs" onClick={() => del(`/api/me/calendars/${c.id}`).then(load)}>
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            {PROVIDERS.map((p) => (
              <button
                key={p.value}
                onClick={() => setProvider(p.value)}
                className={`chip justify-center text-xs ${provider === p.value ? 'bg-ink text-white' : 'bg-white'}`}
              >
                {p.label}
              </button>
            ))}
          </div>
          {hint && <p className="text-xs font-bold text-ink/50">{hint}</p>}
          {provider !== 'demo' && (
            <input
              className="input"
              placeholder="Paste your calendar's ICS / webcal URL"
              value={icsUrl}
              onChange={(e) => setIcsUrl(e.target.value)}
            />
          )}
          {error && <p className="text-sm font-bold text-pop-coral">{error}</p>}
          <button className="btn-primary w-full" disabled={busy || (provider !== 'demo' && !icsUrl.trim())} onClick={connect}>
            {busy ? 'Connecting…' : 'Connect calendar'}
          </button>
        </div>
      </section>

      <section className="card mb-4 p-5">
        <h2 className="font-black">🔁 Auto-sync hangs to your calendar</h2>
        <p className="mt-1 text-sm font-bold text-ink/60">
          Subscribe once and every hang you're invited to shows up in Apple/Google Calendar automatically — reminders included.
          In Apple Calendar: File → New Calendar Subscription. In Google: Other calendars → From URL.
        </p>
        <div className="mt-3 flex gap-2">
          <input className="input flex-1 text-xs" readOnly value={feedUrl} />
          <button
            className="btn-secondary"
            onClick={async () => {
              if (await copyText(feedUrl)) {
                setCopied(true)
                setTimeout(() => setCopied(false), 1500)
              }
            }}
          >
            {copied ? '✓' : 'Copy'}
          </button>
        </div>
      </section>

      <button
        className="btn-secondary w-full"
        onClick={() => {
          signOut()
          nav('/')
        }}
      >
        Sign out
      </button>
    </Shell>
  )
}
