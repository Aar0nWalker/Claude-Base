'use client'
import { useEffect, useState } from 'react'
import Icon from '@/components/icon'

export default function ThemeToggle() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  useEffect(() => {
    const t = (document.documentElement.getAttribute('data-theme') as 'dark' | 'light') || 'dark'
    setTheme(t)
  }, [])

  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.classList.add('theme-transition')
    document.documentElement.setAttribute('data-theme', next)
    try { localStorage.setItem('theme', next) } catch { /* storage blocked (iOS private) */ }
    setTheme(next)
    setTimeout(() => document.documentElement.classList.remove('theme-transition'), 400)
  }

  return (
    <button
      className="theme-btn"
      onClick={toggle}
      aria-label="Переключить тему"
      title={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="ic" />
    </button>
  )
}
