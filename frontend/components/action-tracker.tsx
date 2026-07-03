'use client'

import { useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

const SESSION_KEY = '{{PROJECT_SLUG}}_action_session'

function sessionId(): string {
  try {
    let id = sessionStorage.getItem(SESSION_KEY)
    if (!id) {
      id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
      sessionStorage.setItem(SESSION_KEY, id)
    }
    return id
  } catch {
    return 'no-session-storage'
  }
}

function labelFor(el: HTMLElement): string {
  const direct = el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || ''
  return direct.replace(/\s+/g, ' ').trim().slice(0, 300)
}

function targetFor(el: HTMLElement): string {
  return [
    el.tagName.toLowerCase(),
    el.getAttribute('type') || '',
    el.getAttribute('href') || '',
    el.getAttribute('data-track') || '',
  ].filter(Boolean).join(':').slice(0, 200)
}

export default function ActionTracker() {
  const pathname = usePathname()
  const { isLoggedIn } = useAuth()
  const lastClickRef = useRef(0)

  useEffect(() => {
    if (!isLoggedIn || !pathname) return
    void apiFetch('/backend/tracking/events', {
      method: 'POST',
      silent: true,
      json: { event: 'page_view', path: pathname, session_id: sessionId() },
    }).catch(() => {})
  }, [isLoggedIn, pathname])

  useEffect(() => {
    if (!isLoggedIn) return
    const onClick = (event: MouseEvent) => {
      const now = Date.now()
      if (now - lastClickRef.current < 250) return
      lastClickRef.current = now
      const node = event.target instanceof HTMLElement
        ? event.target.closest('button,a,[role="button"],input,textarea,select')
        : null
      if (!(node instanceof HTMLElement)) return
      void apiFetch('/backend/tracking/events', {
        method: 'POST',
        silent: true,
        json: {
          event: 'click',
          path: window.location.pathname,
          target: targetFor(node),
          label: labelFor(node),
          session_id: sessionId(),
        },
      }).catch(() => {})
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [isLoggedIn])

  return null
}
