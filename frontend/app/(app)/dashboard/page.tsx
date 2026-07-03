'use client'
import Link from 'next/link'
import Icon from '@/components/icon'
import { useAuth } from '@/lib/auth-context'

const QUICK_ACTIONS = [
  { href: '/profile', label: 'Профиль', desc: 'Данные аккаунта и пароль', icon: 'user' },
]

export default function DashboardPage() {
  const { email } = useAuth()
  const name = email ? email.split('@')[0] : ''

  return (
    <div className="content-in">
      <div className="dash-greet">
        {name ? `Привет, ${name}` : 'Добро пожаловать'}
      </div>
      <div className="dash-greet-sub">Это стартовая точка приложения — начни отсюда.</div>

      <div className="qa-grid" style={{ marginTop: 28 }}>
        {QUICK_ACTIONS.map(a => (
          <Link key={a.href} href={a.href} className="qa">
            <Icon name={a.icon} className="ic" />
            <h3>{a.label}</h3>
            <p>{a.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
