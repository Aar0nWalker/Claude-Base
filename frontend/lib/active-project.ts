'use client'
import { useState, useEffect, useCallback } from 'react'

// A generic "active project" pointer some feature can save into. Shared across
// the app via localStorage + a window event so components stay in sync without
// a provider. Adjust the shape / rename once the base has a real domain object.
export interface ActiveProject { id: number; title: string }

const KEY = '{{PROJECT_SLUG}}_active_project'
const EVT = '{{PROJECT_SLUG}}-project-change'

export function readActiveProject(): ActiveProject | null {
  try { const raw = localStorage.getItem(KEY); return raw ? JSON.parse(raw) : null } catch { return null }
}

export function writeActiveProject(p: ActiveProject | null) {
  try { if (p) localStorage.setItem(KEY, JSON.stringify(p)); else localStorage.removeItem(KEY) } catch { /* ignore */ }
  try { window.dispatchEvent(new CustomEvent(EVT)) } catch { /* ignore */ }
}

export function useActiveProject(): [ActiveProject | null, (p: ActiveProject | null) => void] {
  const [project, setProject] = useState<ActiveProject | null>(null)
  useEffect(() => {
    setProject(readActiveProject())
    const sync = () => setProject(readActiveProject())
    window.addEventListener(EVT, sync)
    window.addEventListener('storage', sync)  // other tabs
    return () => { window.removeEventListener(EVT, sync); window.removeEventListener('storage', sync) }
  }, [])
  const set = useCallback((p: ActiveProject | null) => { writeActiveProject(p); setProject(p) }, [])
  return [project, set]
}
