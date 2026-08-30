import type { UserLite } from '../types'

export default function AvatarStack({ users, max = 6 }: { users: UserLite[]; max?: number }) {
  const shown = users.slice(0, max)
  const extra = users.length - shown.length
  return (
    <div className="flex -space-x-2">
      {shown.map((u) => (
        <span
          key={u.id}
          title={u.name}
          className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-ink bg-white text-lg"
        >
          {u.emoji}
        </span>
      ))}
      {extra > 0 && (
        <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-ink bg-pop-sunshine text-xs font-black">
          +{extra}
        </span>
      )}
    </div>
  )
}
