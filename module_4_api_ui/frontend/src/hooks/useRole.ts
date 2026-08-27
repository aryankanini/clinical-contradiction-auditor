import { useState } from 'react'
import { setCredentials } from '../api/client'
import type { Role } from '../api/types'

const STORAGE_KEY_ROLE = 'ca_role'
const STORAGE_KEY_USER = 'ca_user'

function stored(key: string, fallback: string) {
  return localStorage.getItem(key) ?? fallback
}

export function useRole() {
  const [role, _setRole] = useState<Role>(() => stored(STORAGE_KEY_ROLE, 'steward') as Role)
  const [userId, _setUserId] = useState(() => stored(STORAGE_KEY_USER, 'demo-steward'))

  function setRole(r: Role) {
    localStorage.setItem(STORAGE_KEY_ROLE, r)
    setCredentials(userId, r)
    _setRole(r)
  }

  function setUserId(u: string) {
    localStorage.setItem(STORAGE_KEY_USER, u)
    setCredentials(u, role)
    _setUserId(u)
  }

  return { role, userId, setRole, setUserId }
}
