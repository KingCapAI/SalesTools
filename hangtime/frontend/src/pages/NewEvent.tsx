import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { post } from '../api'
import Shell from '../components/Shell'
import type { EventOut, SlotName } from '../types'

const EMOJIS = ['✨', '🌮', '🍜', '🎳', '🥾', '🎬', '🃏', '☕', '🎤', '🏓', '🍦', '⚽']
const SLOTS: { value: SlotName; label: string }[] = [
  { value: 'morning', label: '☀️ Morning' },
  { value: 'afternoon', label: '🌤️ Afternoon' },
  { value: 'evening', label: '🌙 Evening' },
]

export default function NewEvent() {
  const { groupId } = useParams()
  const [params] = useSearchParams()
  const nav = useNavigate()

  const [title, setTitle] = useState(params.get('title') ?? '')
  const [emoji, setEmoji] = useState(params.get('emoji') ?? '✨')
  const [date, setDate] = useState(params.get('date') ?? new Date().toISOString().slice(0, 10))
  const [slot, setSlot] = useState<SlotName>((params.get('slot') as SlotName) ?? 'evening')
  const [startTime, setStartTime] = useState('')
  const [locationName, setLocationName] = useState('')
  const [description, setDescription] = useState('')
  const [reminder, setReminder] = useState(60)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const create = async () => {
    setBusy(true)
    setError('')
    try {
      const e = await post<EventOut>(`/api/groups/${groupId}/events`, {
        title, emoji, date, description,
        location_name: locationName,
        slot: startTime ? null : slot,
        start_time: startTime || null,
        reminder_minutes: reminder,
      })
      nav(`/e/${e.share_code}?created=1`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the hang')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell back={`/g/${groupId}`}>
      <h1 className="mb-4 text-3xl font-black">Plan a hang</h1>
      <div className="card space-y-4 p-5">
        <input className="input" placeholder="What are we doing?" value={title} onChange={(e) => setTitle(e.target.value)} />

        <div className="flex flex-wrap gap-1.5">
          {EMOJIS.map((e) => (
            <button
              key={e}
              onClick={() => setEmoji(e)}
              className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-xl ${
                emoji === e ? 'border-ink bg-pop-sunshine shadow-poplite' : 'border-ink/15 bg-white'
              }`}
            >
              {e}
            </button>
          ))}
        </div>

        <div>
          <label className="mb-1 block text-sm font-black text-ink/60">When</label>
          <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
          <div className="mt-2 flex gap-2">
            {SLOTS.map((s) => (
              <button
                key={s.value}
                onClick={() => {
                  setSlot(s.value)
                  setStartTime('')
                }}
                className={`chip flex-1 justify-center ${slot === s.value && !startTime ? 'bg-ink text-white' : 'bg-white'}`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className="text-sm font-bold text-ink/60">or exact time:</span>
            <input type="time" className="input flex-1" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
          </div>
        </div>

        <input className="input" placeholder="Where? (optional)" value={locationName} onChange={(e) => setLocationName(e.target.value)} />
        <textarea
          className="input"
          rows={2}
          placeholder="Details, dress code, inside jokes…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <div>
          <label className="mb-1 block text-sm font-black text-ink/60">Remind everyone</label>
          <div className="flex gap-2">
            {[
              [30, '30 min before'],
              [60, '1 hr before'],
              [1440, 'a day before'],
            ].map(([mins, label]) => (
              <button
                key={mins}
                onClick={() => setReminder(mins as number)}
                className={`chip flex-1 justify-center text-xs ${reminder === mins ? 'bg-ink text-white' : 'bg-white'}`}
              >
                ⏰ {label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="font-bold text-pop-coral">{error}</p>}
        <button className="btn-primary w-full text-lg" disabled={busy || !title.trim()} onClick={create}>
          {busy ? 'Locking it in…' : 'Lock it in 🔒'}
        </button>
        <p className="text-center text-xs font-bold text-ink/50">
          Everyone in the crew sees it instantly — and it syncs to their own calendars.
        </p>
      </div>
    </Shell>
  )
}
