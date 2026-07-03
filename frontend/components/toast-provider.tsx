'use client'
import { createContext, useCallback, useContext, useEffect, useRef, useState, ReactNode } from 'react'
import { createPortal } from 'react-dom'
import Icon from '@/components/icon'
import { registerErrorToast } from '@/lib/api'

type Kind = 'error' | 'success' | 'info'
interface Toast { id: number; kind: Kind; text: string }

interface ToastApi {
  error: (text: string) => void
  success: (text: string) => void
  info: (text: string) => void
}

const Ctx = createContext<ToastApi>({ error: () => {}, success: () => {}, info: () => {} })
export const useToastApi = () => useContext(Ctx)

const KIND_STYLE: Record<Kind, { bg: string; icon: string }> = {
  error:   { bg: 'rgba(220, 38, 38, 0.97)',  icon: 'alert-circle' },
  success: { bg: 'rgba(16, 163, 110, 0.97)', icon: 'check' },
  info:    { bg: 'rgba(46, 109, 209, 0.97)', icon: 'alert-circle' },
}

export default function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const [mounted, setMounted] = useState(false)
  const seq = useRef(0)
  useEffect(() => setMounted(true), [])

  const remove = useCallback((id: number) => {
    setToasts(list => list.filter(t => t.id !== id))
  }, [])

  const push = useCallback((kind: Kind, text: string) => {
    if (!text) return
    const id = ++seq.current
    setToasts(list => [...list, { id, kind, text }])
    const ttl = kind === 'error' ? 6000 : 3200
    setTimeout(() => remove(id), ttl)
  }, [remove])

  const error = useCallback((t: string) => push('error', t), [push])
  const success = useCallback((t: string) => push('success', t), [push])
  const info = useCallback((t: string) => push('info', t), [push])

  // Let apiFetch surface server errors through the same toast stack.
  useEffect(() => {
    registerErrorToast(error)
    return () => registerErrorToast(null)
  }, [error])

  return (
    <Ctx.Provider value={{ error, success, info }}>
      {children}
      {mounted && createPortal(
        <div
          style={{
            position: 'fixed', top: 16, left: 0, right: 0, zIndex: 3000,
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
            pointerEvents: 'none', padding: '0 16px',
          }}
        >
          {toasts.map(t => {
            const s = KIND_STYLE[t.kind]
            return (
              <div
                key={t.id}
                role="alert"
                style={{
                  pointerEvents: 'auto',
                  maxWidth: 'min(560px, calc(100vw - 32px))',
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '12px 16px', borderRadius: 12,
                  background: s.bg, color: '#fff',
                  boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
                  fontSize: 13.5, fontWeight: 500, lineHeight: 1.4,
                  animation: 'fadeUp 0.2s var(--ease-out) both',
                }}
              >
                <Icon name={s.icon} style={{ width: 18, height: 18, flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{t.text}</span>
                <button
                  onClick={() => remove(t.id)}
                  aria-label="Закрыть"
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer', color: '#fff',
                    padding: 2, display: 'flex', alignItems: 'center', flexShrink: 0,
                  }}
                >
                  <Icon name="x" style={{ width: 16, height: 16 }} />
                </button>
              </div>
            )
          })}
        </div>,
        document.body
      )}
    </Ctx.Provider>
  )
}
