export function formatWhen(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.round((day.getTime() - today.getTime()) / 86400000)
  const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  if (diffDays === 0) return `Today · ${time}`
  if (diffDays === 1) return `Tomorrow · ${time}`
  if (diffDays > 1 && diffDays < 7)
    return `${d.toLocaleDateString([], { weekday: 'long' })} · ${time}`
  return `${d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })} · ${time}`
}

export function formatDay(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00')
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
}

export const SLOT_LABELS: Record<string, string> = {
  morning: 'morning (9–12)',
  afternoon: 'afternoon (12–5)',
  evening: 'evening (5–10)',
}

export function shareEvent(title: string, url: string) {
  const text = `${title} — you in? RSVP here: ${url}`
  if (navigator.share) {
    navigator.share({ title, text, url }).catch(() => {})
  } else {
    // sms: deep link — opens Messages with the invite pre-written
    window.location.href = `sms:?&body=${encodeURIComponent(text)}`
  }
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}
