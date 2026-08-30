import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { get, post } from '../api'
import { useAuth } from '../App'
import Shell from '../components/Shell'
import type { GroupOut } from '../types'

type Preview = { name: string; emoji: string; city: string; member_count: number }

export default function JoinGroup() {
  const { inviteCode } = useParams()
  const { user } = useAuth()
  const nav = useNavigate()
  const [preview, setPreview] = useState<Preview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    get<Preview>(`/api/invites/${inviteCode}`)
      .then(setPreview)
      .catch(() => setError('This invite link is broken or expired 🥲'))
  }, [inviteCode])

  const accept = async () => {
    const g = await post<GroupOut>(`/api/invites/${inviteCode}/accept`)
    nav(`/g/${g.id}`)
  }

  return (
    <Shell>
      <div className="mx-auto max-w-md pt-10">
        {error && <div className="card p-6 text-center font-black">{error}</div>}
        {preview && (
          <div className="card p-6 text-center">
            <div className="text-6xl">{preview.emoji}</div>
            <h1 className="mt-2 text-2xl font-black">You're invited to {preview.name}</h1>
            <p className="mt-1 font-bold text-ink/60">
              {preview.member_count} friends{preview.city ? ` · ${preview.city}` : ''}
            </p>
            {user ? (
              <button className="btn-primary mt-5 w-full text-lg" onClick={accept}>
                Join the crew 🎉
              </button>
            ) : (
              <>
                <p className="mt-4 text-sm font-bold text-ink/60">Grab a name + emoji first (10 seconds, promise)</p>
                <Link to={`/?next=/join/${inviteCode}`} className="btn-primary mt-3 w-full text-lg">
                  Let's go →
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </Shell>
  )
}
