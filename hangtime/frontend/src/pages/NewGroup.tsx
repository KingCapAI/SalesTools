import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { post } from '../api'
import Shell from '../components/Shell'
import type { GroupOut } from '../types'

const EMOJIS = ['🍻', '🏖️', '🎮', '⚽', '🧗', '🍜', '🎉', '🐐', '🔥', '🌮']

export default function NewGroup() {
  const nav = useNavigate()
  const [name, setName] = useState('')
  const [emoji, setEmoji] = useState('🍻')
  const [city, setCity] = useState('')
  const [busy, setBusy] = useState(false)

  const create = async () => {
    setBusy(true)
    try {
      const g = await post<GroupOut>('/api/groups', { name, emoji, city })
      nav(`/g/${g.id}?welcome=1`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell back="/home">
      <h1 className="mb-4 text-3xl font-black">Start a crew</h1>
      <div className="card space-y-3 p-5">
        <input className="input" placeholder="Crew name (The Crew, Sunday FC…)" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input" placeholder="Home city — powers hang ideas" value={city} onChange={(e) => setCity(e.target.value)} />
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
        <button className="btn-primary w-full" disabled={busy || !name.trim()} onClick={create}>
          Create crew →
        </button>
        <p className="text-center text-sm font-bold text-ink/50">
          Next step: text your friends the invite link. No app download required to RSVP.
        </p>
      </div>
    </Shell>
  )
}
