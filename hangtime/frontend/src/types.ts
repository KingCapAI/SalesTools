export type UserLite = { id: number; name: string; emoji: string; city: string }

export type Rsvp = {
  user_id: number | null
  name: string
  emoji: string
  status: 'going' | 'maybe' | 'cant'
  note: string
}

export type EventOut = {
  id: number
  group_id: number
  title: string
  emoji: string
  description: string
  location_name: string
  address: string
  start: string
  end: string
  reminder_minutes: number
  share_code: string
  created_by: UserLite | null
  rsvps: Rsvp[]
  share_url: string
  group?: { id: number; name: string; emoji: string }
  is_member?: boolean
  my_status?: Rsvp['status'] | null
}

export type GroupOut = {
  id: number
  name: string
  emoji: string
  city: string
  invite_code: string
  members: UserLite[]
  upcoming_events: EventOut[]
  invite_url?: string
}

export type SlotName = 'morning' | 'afternoon' | 'evening'

export type GridSlot = { slot: SlotName; free_ids: number[]; free_count: number }
export type GridDay = { date: string; weekday: string; is_weekend: boolean; slots: GridSlot[] }

export type BestTime = {
  date: string
  weekday: string
  slot: SlotName
  free_ids: number[]
  free_count: number
}

export type Availability = {
  members: Record<string, UserLite>
  grid: GridDay[]
  best_times: BestTime[]
}

export type Idea = { emoji: string; title: string; blurb: string; vibe: string; slot: SlotName; cost: string }

export type ChatMessage = { id: number; user: UserLite | null; body: string; created_at: string }

export type CalendarConn = { id: number; provider: string; label: string; last_synced_at: string | null }

export type MeFull = UserLite & { handle: string; feed_url: string; calendars: CalendarConn[] }
