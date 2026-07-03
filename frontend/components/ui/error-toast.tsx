'use client'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import Icon from '@/components/icon'

interface Props {
  message: string | null
  onClose: () => void
  durationMs?: number
  actionLabel?: string
  actionHref?: string
  variant?: 'error' | 'warning'
}

export default function ErrorToast({ message, onClose, durationMs = 10000, actionLabel, actionHref, variant = 'error' }: Props) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  useEffect(() => {
    if (!message) return
    const id = setTimeout(onClose, durationMs)
    return () => clearTimeout(id)
  }, [message, durationMs, onClose])

  if (!mounted || !message) return null
  const isWarning = variant === 'warning'
  const bg = isWarning ? 'rgba(202, 138, 4, 0.97)' : 'rgba(220, 38, 38, 0.97)'
  const actionColor = isWarning ? '#92400e' : '#b91c1c'

  // Outer container handles centering; inner element runs the animation, so the
  // keyframe's transform can't override a centering transform (was the off-center bug).
  return createPortal(
    <div
      style={{
        position: 'fixed', top: 16, left: 0, right: 0, zIndex: 3000,
        display: 'flex', justifyContent: 'center', pointerEvents: 'none',
        padding: '0 16px',
      }}
    >
      <div
        style={{
          pointerEvents: 'auto',
          maxWidth: 'min(560px, calc(100vw - 32px))',
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 16px', borderRadius: 12,
          background: bg, color: '#fff',
          boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
          fontSize: 13.5, fontWeight: 500, lineHeight: 1.4,
          animation: 'fadeUp 0.2s var(--ease-out) both',
        }}
        role="alert"
      >
        <Icon name="alert-circle" style={{ width: 18, height: 18, flexShrink: 0 }} />
        <span style={{ flex: 1 }}>{message}</span>
        {actionLabel && actionHref && (
          <a
            href={actionHref}
            style={{
              flexShrink: 0, padding: '6px 12px', borderRadius: 8,
              background: '#fff', color: actionColor, fontWeight: 700, fontSize: 12.5,
              textDecoration: 'none', whiteSpace: 'nowrap',
            }}
          >
            {actionLabel}
          </a>
        )}
        <button
          onClick={onClose}
          style={{
            background: 'none', border: 'none', cursor: 'pointer', color: '#fff',
            padding: 2, display: 'flex', alignItems: 'center', flexShrink: 0,
          }}
        >
          <Icon name="x" style={{ width: 16, height: 16 }} />
        </button>
      </div>
    </div>,
    document.body
  )
}
