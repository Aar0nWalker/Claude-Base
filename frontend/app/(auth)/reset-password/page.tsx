'use client'
import { useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Icon from '@/components/icon'
import Field from '@/components/ui/field'
import { apiFetch } from '@/lib/api'

function ResetPasswordInner() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function handleReset() {
    if (password !== confirm) { setError('Пароли не совпадают'); return }
    if (password.length < 8) { setError('Пароль должен быть не менее 8 символов'); return }
    if (!token) { setError('Неверная ссылка'); return }
    setBusy(true)
    setError(null)
    try {
      await apiFetch('/backend/auth/reset-password', {
        method: 'POST', json: { token, new_password: password }, silent: true,
      })
      setDone(true)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth">
      <div className="auth-glow" />
      <div className="auth-card">
        <div className="auth-brand">{'{{PROJECT_NAME}}'}</div>

        {done ? (
          <>
            <div style={{ textAlign: 'center', margin: '8px 0 18px' }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, background: 'var(--success-soft)', color: '#3fe0b0', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <Icon name="circle-check" style={{ width: 26, height: 26 }} />
              </div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>Пароль изменён</div>
            </div>
            <p className="auth-sub" style={{ marginBottom: 22 }}>Теперь можете войти с новым паролем.</p>
            <Link href="/login" className="btn btn-grad btn-block btn-lg">
              Войти
            </Link>
          </>
        ) : (
          <>
            <p className="auth-sub" style={{ marginTop: 4 }}>Новый пароль</p>
            <div className="auth-form">
              <Field label="Новый пароль" type="password" placeholder="••••••••" autoFocus value={password} onChange={setPassword} />
              <Field label="Повтор пароля" type="password" placeholder="••••••••" value={confirm} onChange={setConfirm} />
              {error && (
                <div style={{ fontSize: 13, color: 'var(--error)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Icon name="alert-circle" style={{ width: 14, height: 14, flexShrink: 0 }} />
                  {error}
                </div>
              )}
              <button
                className="btn btn-grad btn-block btn-lg"
                onClick={handleReset}
                disabled={busy || !password || !confirm}
              >
                {busy ? 'Сохраняем…' : 'Сохранить пароль'}
              </button>
            </div>
            <div className="auth-alt">
              <Link href="/login">← Вернуться ко входу</Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordInner />
    </Suspense>
  )
}
