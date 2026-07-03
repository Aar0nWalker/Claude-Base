'use client'
import { createContext, useCallback, useContext, useEffect, useRef, useState, ReactNode } from 'react'
import { createPortal } from 'react-dom'
import Icon from '@/components/icon'

interface ConfirmOptions {
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
  // When set, the user must type this exact string to enable the confirm button
  // (extra guard for destructive actions like deleting a project with its media).
  requireText?: string
}

// Promise-based confirm — replaces the native window.confirm(). Accepts either a
// plain message string or a full options object.
type ConfirmFn = (opts: ConfirmOptions | string) => Promise<boolean>

const Ctx = createContext<ConfirmFn>(async () => false)
export const useConfirm = () => useContext(Ctx)

interface State extends ConfirmOptions { open: boolean }

export default function ConfirmProvider({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false)
  const [state, setState] = useState<State>({ open: false, message: '' })
  const [typed, setTyped] = useState('')
  const resolver = useRef<(v: boolean) => void>(() => {})
  useEffect(() => setMounted(true), [])

  const confirm = useCallback<ConfirmFn>((opts) => {
    const o = typeof opts === 'string' ? { message: opts } : opts
    setTyped('')
    setState({ open: true, ...o })
    return new Promise<boolean>((res) => { resolver.current = res })
  }, [])

  const locked = !!state.requireText && typed.trim() !== state.requireText.trim()

  const close = useCallback((result: boolean) => {
    setState((s) => ({ ...s, open: false }))
    resolver.current(result)
  }, [])

  useEffect(() => {
    if (!state.open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close(false)
      if (e.key === 'Enter' && !locked) close(true)
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = prev }
  }, [state.open, locked, close])

  return (
    <Ctx.Provider value={confirm}>
      {children}
      {mounted && state.open && createPortal(
        <div className="modal-overlay" style={{ zIndex: 3500, padding: 16 }} onClick={() => close(false)}>
          <div
            role="alertdialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--surface-1)', border: '1px solid var(--border-2)', borderRadius: 16,
              maxWidth: 420, width: '100%', padding: '22px 22px 18px',
              boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
              animation: 'scaleIn 0.22s var(--ease-out) both',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 11, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: state.danger ? 'rgba(255,84,112,0.14)' : 'var(--surface-2)',
                color: state.danger ? '#ff869b' : 'var(--accent)',
              }}>
                <Icon name={state.danger ? 'trash-2' : 'alert-circle'} style={{ width: 20, height: 20 }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--fg-1)', marginBottom: state.message ? 6 : 0 }}>
                  {state.title ?? 'Подтверждение'}
                </div>
                <div style={{ fontSize: 13.5, color: 'var(--fg-2)', lineHeight: 1.5 }}>{state.message}</div>
              </div>
            </div>
            {state.requireText && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12.5, color: 'var(--fg-3)', marginBottom: 6 }}>
                  Для подтверждения введите: <b style={{ color: 'var(--fg-1)' }}>{state.requireText}</b>
                </div>
                <input
                  autoFocus value={typed} onChange={(e) => setTyped(e.target.value)}
                  placeholder={state.requireText}
                  style={{
                    width: '100%', padding: '9px 11px', borderRadius: 10, fontSize: 13.5,
                    background: 'var(--surface-2)', border: '1px solid var(--border-2)', color: 'var(--fg-1)',
                  }}
                />
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, marginTop: 22, justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => close(false)}>
                {state.cancelLabel ?? 'Отмена'}
              </button>
              <button
                className={`btn${state.danger ? '' : ' btn-grad'}`}
                autoFocus={!state.requireText}
                disabled={locked}
                onClick={() => { if (!locked) close(true) }}
                style={state.danger
                  ? { background: '#e5384f', color: '#fff', border: '1px solid #e5384f', opacity: locked ? 0.5 : 1, cursor: locked ? 'default' : 'pointer' }
                  : { opacity: locked ? 0.5 : 1, cursor: locked ? 'default' : 'pointer' }}
              >
                {state.confirmLabel ?? (state.danger ? 'Удалить' : 'Подтвердить')}
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </Ctx.Provider>
  )
}
