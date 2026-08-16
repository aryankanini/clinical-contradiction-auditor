import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { setIdentity } from '../api/client'
import type { Role } from '../api/types'

const STORAGE_KEY = 'clinical-auditor-identity'

interface Identity {
  userId: string
  role: Role
}

interface RoleContextValue extends Identity {
  setRole: (role: Role) => void
  setUserId: (userId: string) => void
}

const DEFAULT: Identity = { userId: 'demo-steward', role: 'steward' }

const RoleContext = createContext<RoleContextValue | null>(null)

function readStored(): Identity {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT
    const parsed = JSON.parse(raw) as Partial<Identity>
    if (!parsed.userId || !parsed.role) return DEFAULT
    return { userId: parsed.userId, role: parsed.role }
  } catch {
    return DEFAULT
  }
}

export function RoleProvider({ children }: { children: ReactNode }) {
  const [identity, setLocalIdentity] = useState<Identity>(readStored)

  // The API client reads identity from module state, so it has to be kept in step
  // with React state on every change — including the first render.
  useEffect(() => {
    setIdentity(identity)
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(identity))
  }, [identity])

  const setRole = useCallback((role: Role) => {
    setLocalIdentity((current) => ({ ...current, role }))
  }, [])

  const setUserId = useCallback((userId: string) => {
    setLocalIdentity((current) => ({ ...current, userId }))
  }, [])

  const value = useMemo<RoleContextValue>(
    () => ({ ...identity, setRole, setUserId }),
    [identity, setRole, setUserId],
  )

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole(): RoleContextValue {
  const context = useContext(RoleContext)
  if (!context) {
    throw new Error('useRole must be used inside a RoleProvider')
  }
  return context
}
