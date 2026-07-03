// A new deploy changes Next.js chunk hashes. A tab still on the old build hits a
// 404 for `/_next/static/chunks/*` on its next client-side navigation, throwing
// ChunkLoadError. The cure is just to reload onto the new build — so instead of
// showing a scary "что-то пошло не так", the error boundary reloads silently.
// Guarded via sessionStorage so a genuinely-broken chunk can't loop forever.

export function isChunkLoadError(error: { name?: string; message?: string } | null | undefined): boolean {
  if (!error) return false
  return error.name === 'ChunkLoadError'
    || /loading (css )?chunk|loading chunk \d+ failed|failed to (load|fetch)|importing a module script failed|error loading dynamically imported module|dynamically imported module/i.test(error.message || '')
}

const RELOAD_KEY = '{{PROJECT_SLUG}}_chunk_reload_at'

// Triggers one reload. Returns true if it fired (caller should render a neutral
// placeholder); false if a reload happened too recently (show the error UI).
export function recoverFromChunkError(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const last = Number(sessionStorage.getItem(RELOAD_KEY) || '0')
    if (Date.now() - last > 10_000) {
      sessionStorage.setItem(RELOAD_KEY, String(Date.now()))
      window.location.reload()
      return true
    }
  } catch { /* sessionStorage blocked — fall through to the error UI */ }
  return false
}

// The React error boundary only catches errors thrown during render. A stale chunk
// after a deploy often fails OUTSIDE render — as a rejected dynamic import during
// client-side navigation, or a <script>/<link> 404 — so the page just goes blank
// and in-progress state (e.g. a running generation) never re-attaches. Install
// global listeners that auto-reload onto the fresh build in those cases too.
let installed = false
export function installChunkErrorAutoReload(): void {
  if (typeof window === 'undefined' || installed) return
  installed = true
  // Rejected dynamic import (router navigation loading a route/chunk).
  window.addEventListener('unhandledrejection', (ev) => {
    if (isChunkLoadError(ev?.reason as { name?: string; message?: string })) recoverFromChunkError()
  })
  // <script>/<link> 404 for a stale /_next asset (resource errors need capture phase).
  window.addEventListener('error', (ev) => {
    const t = ev.target as (HTMLScriptElement & HTMLLinkElement) | null
    const url = t ? (t.src || t.href || '') : ''
    if (url && /\/_next\/static\//.test(url)) recoverFromChunkError()
    else if (isChunkLoadError((ev as ErrorEvent).error)) recoverFromChunkError()
  }, true)
}
