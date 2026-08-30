import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'

export default function Shell({ children, back }: { children: React.ReactNode; back?: string }) {
  const { user } = useAuth()
  const nav = useNavigate()
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-xl flex-col px-4 pb-10 pt-4">
      <header className="mb-4 flex items-center justify-between">
        {back ? (
          <button onClick={() => nav(back)} className="chip bg-white" aria-label="Back">
            ← back
          </button>
        ) : (
          <Link to={user ? '/home' : '/'} className="text-2xl font-black tracking-tight">
            🤙 Hangtime
          </Link>
        )}
        {user && (
          <Link to="/settings" className="chip bg-pop-sunshine" title="Settings">
            <span>{user.emoji}</span> {user.name}
          </Link>
        )}
      </header>
      <main className="flex-1">{children}</main>
    </div>
  )
}
