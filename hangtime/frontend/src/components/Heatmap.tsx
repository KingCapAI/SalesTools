import clsx from 'clsx'
import { useState } from 'react'
import type { Availability, GridSlot, SlotName } from '../types'

const SLOT_META: Record<SlotName, { label: string; emoji: string }> = {
  morning: { label: 'AM', emoji: '☀️' },
  afternoon: { label: 'Mid', emoji: '🌤️' },
  evening: { label: 'Eve', emoji: '🌙' },
}

function cellStyle(count: number, total: number) {
  if (total === 0) return { backgroundColor: '#f1ede7' }
  const ratio = count / total
  if (ratio === 0) return { backgroundColor: '#f1ede7' }
  return { backgroundColor: `rgba(107, 203, 119, ${0.25 + ratio * 0.75})` }
}

export type CellPick = { date: string; weekday: string; slot: SlotName; free_ids: number[] }

export default function Heatmap({
  availability,
  onPick,
}: {
  availability: Availability
  onPick: (cell: CellPick) => void
}) {
  const total = Object.keys(availability.members).length
  const [selected, setSelected] = useState<string | null>(null)

  const pick = (date: string, weekday: string, slot: GridSlot) => {
    setSelected(`${date}|${slot.slot}`)
    onPick({ date, weekday, slot: slot.slot, free_ids: slot.free_ids })
  }

  return (
    <div>
      <div className="mb-1 grid grid-cols-[3.5rem_1fr_1fr_1fr] gap-1 text-center text-xs font-black text-ink/60">
        <span />
        {(['morning', 'afternoon', 'evening'] as SlotName[]).map((s) => (
          <span key={s}>
            {SLOT_META[s].emoji} {SLOT_META[s].label}
          </span>
        ))}
      </div>
      <div className="flex max-h-[22rem] flex-col gap-1 overflow-y-auto pr-1">
        {availability.grid.map((day) => {
          const d = new Date(day.date + 'T00:00:00')
          return (
            <div key={day.date} className="grid grid-cols-[3.5rem_1fr_1fr_1fr] items-stretch gap-1">
              <div
                className={clsx(
                  'flex flex-col items-center justify-center rounded-xl text-xs font-black',
                  day.is_weekend ? 'bg-pop-sunshine/60' : '',
                )}
              >
                <span>{day.weekday}</span>
                <span className="text-ink/50">{d.getDate()}</span>
              </div>
              {day.slots.map((slot) => {
                const key = `${day.date}|${slot.slot}`
                const everyone = total > 0 && slot.free_count === total
                return (
                  <button
                    key={slot.slot}
                    onClick={() => pick(day.date, day.weekday, slot)}
                    style={cellStyle(slot.free_count, total)}
                    className={clsx(
                      'flex h-10 items-center justify-center rounded-xl border-2 text-sm font-black transition',
                      selected === key ? 'border-ink shadow-poplite' : 'border-transparent',
                    )}
                  >
                    {everyone ? '🔥' : slot.free_count > 0 ? slot.free_count : ''}
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>
      <p className="mt-2 text-center text-xs font-bold text-ink/50">
        greener = more friends free · 🔥 = everyone's free · tap a slot to plan it
      </p>
    </div>
  )
}
