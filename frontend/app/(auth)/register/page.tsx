'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Field from '@/components/ui/field'
import Icon from '@/components/icon'
import { useAuth } from '@/lib/auth-context'

export default function RegisterPage() {
  const router = useRouter()
  const { register, isLoggedIn, isLoading } = useAuth()
  const [done, setDone] = useState(false)
  const [doneEmail, setDoneEmail] = useState('')

  useEffect(() => {
    if (!isLoading && isLoggedIn) router.push('/dashboard')
  }, [isLoggedIn, isLoading])

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleRegister() {
    setError(null)
    if (password !== confirm) {
      setError('Пароли не совпадают')
      return
    }
    if (password.length < 8) {
      setError('Пароль должен быть не менее 8 символов')
      return
    }
    setBusy(true)
    try {
      await register(email, password)
      router.push('/dashboard')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Ошибка регистрации'
      if (msg === 'verify_email_sent') {
        setDoneEmail(email)
        setDone(true)
        return
      }
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="auth">
        <div className="auth-glow" />
        <div className="auth-card">
          <div className="auth-brand">{'{{PROJECT_NAME}}'}</div>
          <div style={{ textAlign: 'center', margin: '8px 0 18px' }}>
            <div style={{ width: 56, height: 56, borderRadius: 16, background: 'var(--success-soft)', color: '#3fe0b0', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <Icon name="mail-check" style={{ width: 26, height: 26 }} />
            </div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>Проверьте почту</div>
          </div>
          <p className="auth-sub" style={{ marginBottom: 22 }}>
            Мы отправили письмо с подтверждением на <strong>{doneEmail}</strong>. Перейдите по ссылке в письме для входа.
          </p>
          <Link href="/login" className="btn btn-secondary btn-block btn-lg">
            Вернуться ко входу
          </Link>
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
          <Link href="/login" className="auth-tab">Войти</Link>
          <div className="auth-tab active">Регистрация</div>
        </div>
        <div className="auth-form">
          <Field label="Email" type="email" placeholder="you@example.com" autoFocus value={email} onChange={setEmail} />
          <Field label="Пароль" type="password" placeholder="••••••••" value={password} onChange={setPassword} />
          <Field label="Повтор пароля" type="password" placeholder="••••••••" value={confirm} onChange={setConfirm} />
          {error && (
            <div style={{ fontSize: 13, color: 'var(--error)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="alert-circle" style={{ width: 14, height: 14, flexShrink: 0 }} />
              {error}
            </div>
          )}
          <label className="checkbox-row">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>
              Я соглашаюсь на обработку персональных данных и принимаю{' '}
              <Link href="/privacy" target="_blank">Политику конфиденциальности</Link> и{' '}
              <Link href="/terms" target="_blank">Пользовательское соглашение</Link>.
            </span>
          </label>
          <button
            className="btn btn-grad btn-block btn-lg"
            disabled={!consent || busy || !email || !password || !confirm}
            onClick={handleRegister}
          >
            {busy ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
          </button>
        </div>
        <div className="auth-alt">
          <span>Уже есть аккаунт? <Link href="/login">Войти</Link></span>
        </div>
      </div>
    </div>
  )
}
