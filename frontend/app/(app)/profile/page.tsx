'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Field from '@/components/ui/field'
import { useAuth } from '@/lib/auth-context'
import { apiFetch } from '@/lib/api'

export default function ProfilePage() {
  const router = useRouter()
  const { email, logout } = useAuth()

  const [pwCurrent, setPwCurrent] = useState('')
  const [pwNew, setPwNew] = useState('')
  const [pwConfirm, setPwConfirm] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null)

  async function changePassword() {
    if (pwNew !== pwConfirm) { setPwMsg({ ok: false, text: 'Пароли не совпадают' }); return }
    if (pwNew.length < 8) { setPwMsg({ ok: false, text: 'Новый пароль — не менее 8 символов' }); return }
    setPwSaving(true); setPwMsg(null)
    try {
      // Backend bumps token_version (kills other sessions) and refreshes this
      // session's httpOnly cookie so the current tab stays logged in.
      await apiFetch('/backend/auth/me/password', {
        method: 'PUT',
        json: { current_password: pwCurrent, new_password: pwNew },
        silent: true,
      })
      setPwMsg({ ok: true, text: 'Пароль изменён' })
      setPwCurrent(''); setPwNew(''); setPwConfirm('')
    } catch (e: unknown) {
      setPwMsg({ ok: false, text: e instanceof Error ? e.message : 'Ошибка' })
    } finally { setPwSaving(false) }
  }

  function handleLogout() {
    logout()
    router.push('/')
  }

  return (
    <div className="content-in">
      <div className="profile-grid">
        <div className="card">
          <h3>Аккаунт</h3>
          <div className="kv"><span className="k">Email</span><span className="v">{email || '—'}</span></div>
          <hr style={{ margin: '24px 0', border: 'none', borderTop: '1px solid var(--border-1)' }} />
          <button
            className="btn btn-ghost"
            style={{ color: 'var(--danger)', borderColor: 'var(--danger-soft)' }}
            onClick={handleLogout}
          >
            Выйти из аккаунта
          </button>
        </div>

        <div className="card">
          <h3>Смена пароля</h3>
          <div className="auth-form">
            <Field label="Текущий пароль" type="password" placeholder="••••••••"
              value={pwCurrent} onChange={setPwCurrent} />
            <Field label="Новый пароль" type="password" placeholder="••••••••"
              value={pwNew} onChange={setPwNew} />
            <Field label="Повтор нового пароля" type="password" placeholder="••••••••"
              value={pwConfirm} onChange={setPwConfirm} />
            {pwMsg && (
              <div style={{ fontSize: 12.5, color: pwMsg.ok ? 'var(--success)' : 'var(--error)' }}>
                {pwMsg.text}
              </div>
            )}
            <button
              className="btn btn-primary btn-block"
              style={{ marginTop: 6 }}
              disabled={!pwCurrent || !pwNew || !pwConfirm || pwSaving}
              onClick={changePassword}
            >
              {pwSaving ? 'Сохранение…' : 'Сохранить пароль'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
