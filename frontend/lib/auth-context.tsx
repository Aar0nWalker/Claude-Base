'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { apiFetch, setSessionActive, registerUnauthorized } from '@/lib/api'

interface AuthProfile {
  email: string
  is_admin: boolean
}

interface AuthCtx {
  email: string | null
  isAdmin: boolean
  isLoggedIn: boolean
  isLoading: boolean
  refreshSession: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

async function fetchMe(): Promise<AuthProfile | null> {
  try {
    return await apiFetch<AuthProfile>('/backend/auth/me', { silent: true })
  } catch {
    return null
  }
}

const Ctx = createContext<AuthCtx>({
  email: null,
  isAdmin: false,
  isLoggedIn: false,
  isLoading: true,
  refreshSession: async () => {},
  login: async () => {},
  register: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  function applyProfile(profile: AuthProfile | null) {
    setSessionActive(!!profile)
    setEmail(profile?.email ?? null)
    setIsAdmin(!!profile?.is_admin)
  }

  function clearLocalSession() {
    setSessionActive(false)
    setEmail(null)
    setIsAdmin(false)
  }

  async function refreshSession() {
    applyProfile(await fetchMe())
  }

  useEffect(() => {
    registerUnauthorized(() => {
      clearLocalSession()
    })
    refreshSession().finally(() => setIsLoading(false))
    return () => registerUnauthorized(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auth calls use silent:true — the login/register pages render their own
  // inline messages, so we don't want a duplicate global toast.
  async function login(emailVal: string, password: string) {
    const profile = await apiFetch<AuthProfile>('/backend/auth/login', {
      method: 'POST', json: { email: emailVal, password }, silent: true,
    })
    applyProfile(profile)
  }

  async function register(emailVal: string, password: string) {
    const body = await apiFetch<{ status?: string }>('/backend/auth/register', {
      method: 'POST', json: { email: emailVal, password }, silent: true,
    })
    if (body.status === 'verify_email_sent') throw new Error('verify_email_sent')
  }

  function logout() {
    void apiFetch('/backend/auth/logout', { method: 'POST', silent: true }).catch(() => {})
    clearLocalSession()
  }

  return (
    <Ctx.Provider value={{ email, isAdmin, isLoggedIn: !!email, isLoading, refreshSession, login, register, logout }}>
      {children}
    </Ctx.Provider>
  )
}

export const useAuth = () => useContext(Ctx)
