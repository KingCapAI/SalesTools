import { createContext, useContext, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { clearSession, getStoredUser, saveSession, type Me } from './api'
import EventPage from './pages/EventPage'
import GroupPage from './pages/GroupPage'
import Home from './pages/Home'
import JoinGroup from './pages/JoinGroup'
import NewEvent from './pages/NewEvent'
import NewGroup from './pages/NewGroup'
import Settings from './pages/Settings'
import Welcome from './pages/Welcome'

type AuthCtx = {
  user: Me | null
  signIn: (token: string, user: Me) => void
  signOut: () => void
}

const Ctx = createContext<AuthCtx>({ user: null, signIn: () => {}, signOut: () => {} })

export const useAuth = () => useContext(Ctx)

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const loc = useLocation()
  if (!user) return <Navigate to={`/?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />
  return <>{children}</>
}

export default function App() {
  const [user, setUser] = useState<Me | null>(getStoredUser())

  const value: AuthCtx = {
    user,
    signIn: (token, u) => {
      saveSession(token, u)
      setUser(u)
    },
    signOut: () => {
      clearSession()
      setUser(null)
    },
  }

  return (
    <Ctx.Provider value={value}>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/home" element={<RequireAuth><Home /></RequireAuth>} />
        <Route path="/groups/new" element={<RequireAuth><NewGroup /></RequireAuth>} />
        <Route path="/g/:groupId" element={<RequireAuth><GroupPage /></RequireAuth>} />
        <Route path="/g/:groupId/new" element={<RequireAuth><NewEvent /></RequireAuth>} />
        <Route path="/join/:inviteCode" element={<JoinGroup />} />
        <Route path="/e/:shareCode" element={<EventPage />} />
        <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Ctx.Provider>
  )
}
