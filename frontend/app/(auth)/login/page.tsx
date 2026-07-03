'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Field from '@/components/ui/field'
import Icon from '@/components/icon'
import { useAuth } from '@/lib/auth-context'
import { apiFetch } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const { login, isLoggedIn, isLoading } = useAuth()
  const [mode, setMode] = useState<'login' | 'forgot'>('login')
  const [sent, setSent] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [forgotBusy, setForgotBusy] = useState(false)
  const [forgotError, setForgotError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoading && isLoggedIn) router.push('/dashboard')
  }, [isLoggedIn, isLoading])

  async function handleLogin() {
    if (!email.trim() || !password.trim()) {
      setError('Введи email и пароль')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      // Redirect handled by the isLoggedIn effect.
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Неверный email или пароль'
      if (msg === 'email_not_verified') {
        setError('Email не подтверждён — проверьте почту и перейдите по ссылке из письма')
      } else {
        setError(msg)
      }
    } finally {
      setBusy(false)
    }
  }

  async function handleForgot() {
    if (!email.trim()) return
    setForgotBusy(true)
    setForgotError(null)
    try {
      await apiFetch('/backend/auth/forgot-password', {
        method: 'POST', json: { email }, silent: true,
      })
      setSent(true)
    } catch (e: unknown) {
      setForgotError(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setForgotBusy(false)
    }
  }

  if (mode === 'forgot') {
    return (
      <div className="auth">
        <div className="auth-glow" />
        <div className="auth-card">
          <div className="auth-brand">{'{{PROJECT_NAME}}'}</div>
          {sent ? (
            <>
              <div style={{ textAlign: 'center', margin: '8px 0 18px' }}>
                <div style={{ width: 56, height: 56, borderRadius: 16, background: 'var(--success-soft)', color: '#3fe0b0', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                  <Icon name="mail-check" style={{ width: 26, height: 26 }} />
                </div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>Письмо отправлено</div>
              </div>
              <p className="auth-sub" style={{ marginBottom: 22 }}>Мы отправили ссылку для сброса пароля на твой email. Проверь почту и спам.</p>
              <button className="btn btn-secondary btn-block btn-lg" onClick={() => { setMode('login'); setSent(false) }}>
                Вернуться ко входу
              </button>
            </>
          ) : (
            <>
              <p className="auth-sub" style={{ marginTop: 4 }}>Восстановление пароля</p>
              <div className="auth-form">
                <Field label="Email" type="email" placeholder="you@example.ru" autoFocus value={email} onChange={setEmail} />
                <p style={{ fontSize: 13, color: 'var(--fg-3)', margin: '-4px 0 0', lineHeight: 1.5 }}>
                  Пришлём ссылку для сброса пароля на этот адрес.
                </p>
                {forgotError && (
                  <div style={{ fontSize: 13, color: 'var(--error)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Icon name="alert-circle" style={{ width: 14, height: 14, flexShrink: 0 }} />
                    {forgotError}
                  </div>
                )}
                <button
                  className="btn btn-grad btn-block btn-lg"
                  onClick={handleForgot}
                  disabled={forgotBusy || !email.trim()}
                >
                  {forgotBusy ? 'Отправляем…' : 'Отправить ссылку'}
                </button>
              </div>
              <div className="auth-alt">
                <a style={{ cursor: 'pointer' }} onClick={() => setMode('login')}>← Вернуться ко входу</a>
              </div>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="auth">
      <div className="auth-glow" />
      <div className="auth-card">
        <div className="auth-brand">{'{{PROJECT_NAME}}'}</div>
        <p className="auth-sub">{'{{PROJECT_TAGLINE}}'}</p>
        <div className="auth-tabs">
          <div className="auth-tab active">Войти</div>
          <Link href="/register" className="auth-tab">Регистрация</Link>
        </div>
        <div className="auth-form">
          <Field label="Email" type="email" placeholder="you@example.ru" autoFocus value={email} onChange={setEmail} />
          <Field label="Пароль" type="password" placeholder="••••••••" value={password} onChange={setPassword} />
          {error && (
            <div style={{ fontSize: 13, color: 'var(--error)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="alert-circle" style={{ width: 14, height: 14, flexShrink: 0 }} />
              {error}
            </div>
          )}
          <div
            style={{ fontSize: 14, color: 'var(--accent)', cursor: 'pointer', fontWeight: 600 }}
            onClick={() => { setMode('forgot'); setError(null) }}
          >
            Забыли пароль?
          </div>
          <button
            className="btn btn-grad btn-block btn-lg"
            onClick={handleLogin}
            disabled={busy}
          >
            {busy ? 'Вход…' : 'Войти'}
          </button>
        </div>
        <div className="auth-alt">
          <span>Нет аккаунта? <Link href="/register">Зарегистрироваться</Link></span>
        </div>
      </div>
    </div>
  )
}
