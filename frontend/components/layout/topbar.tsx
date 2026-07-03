'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import Icon from '@/components/icon'
import ThemeToggle from '@/components/theme-toggle'
import { useAuth } from '@/lib/auth-context'

export default function Topbar() {
  const pathname = usePathname()
  const { email, isAdmin } = useAuth()
  const initial = email ? email[0].toUpperCase() : '?'
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!menuOpen) return
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [menuOpen])

  useEffect(() => { setMenuOpen(false) }, [pathname])

  return (
    <header className="topbar">
      <div className="topbar-left">
        <Link href="/dashboard" className="topbar-brand">
          <span className="topbar-brand-name">{'{{PROJECT_NAME}}'}</span>
        </Link>
        <div className="topbar-divider" />
        <nav className="topbar-nav">
          <Link
            href="/dashboard"
            title="Дашборд"
            className={`topbar-tab${pathname === '/dashboard' ? ' active' : ''}`}
          >
            <Icon name="layout-dashboard" className="ic" />
            <span className="topbar-tab-label">Дашборд</span>
          </Link>
        </nav>
      </div>

      <div className="topbar-right">
        {isAdmin && (
          <Link
            href="/admin"
            className={`topbar-tab topbar-tab-secondary${pathname === '/admin' ? ' active' : ''}`}
            style={{ marginRight: 4 }}
            title="Администрирование"
          >
            <Icon name="shield" className="ic" />
          </Link>
        )}
        <ThemeToggle />
        <div className="profile-wrap" ref={menuRef}>
          <button
            type="button"
            className="avatar-dot"
            title="Меню профиля"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(v => !v)}
          >
            {initial}
          </button>
          {menuOpen && (
            <div className="profile-menu" role="menu">
              <Link href="/profile" role="menuitem"><Icon name="user" className="ic" />Профиль</Link>
              {isAdmin && (
                <Link href="/admin" role="menuitem"><Icon name="shield" className="ic" />Администрирование</Link>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
