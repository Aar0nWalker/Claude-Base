'use client'
import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import Icon from '@/components/icon'
import { useAuth } from '@/lib/auth-context'
import { apiFetch } from '@/lib/api'

function VerifyEmailInner() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { refreshSession } = useAuth()
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setErrorMsg('Ссылка недействительна')
      setStatus('error')
      return
    }
    apiFetch(`/backend/auth/verify-email?token=${encodeURIComponent(token)}`, { silent: true })
      .then(async () => {
        await refreshSession()
        setStatus('ok')
        setTimeout(() => router.push('/dashboard'), 1500)
      })
      .catch(e => {
        setErrorMsg(e instanceof Error ? e.message : 'Ошибка подтверждения')
        setStatus('error')
      })
  }, [])

  return (
    <div className="auth">
      <div className="auth-glow" />
      <div className="auth-card">
        <div className="auth-brand">{'{{PROJECT_NAME}}'}</div>

        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div className="spinner" style={{ width: 36, height: 36, borderWidth: 2, margin: '0 auto 16px' }} />
            <p className="auth-sub">Подтверждаем email…</p>
          </div>
        )}

        {status === 'ok' && (
          <>
            <div style={{ textAlign: 'center', margin: '8px 0 18px' }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, background: 'var(--success-soft)', color: '#3fe0b0', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <Icon name="circle-check" style={{ width: 26, height: 26 }} />
              </div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>Email подтверждён!</div>
            </div>
            <p className="auth-sub" style={{ marginBottom: 22 }}>Переходим в дашборд…</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{ textAlign: 'center', margin: '8px 0 18px' }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, background: 'var(--error-soft)', color: 'var(--error)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <Icon name="circle-x" style={{ width: 26, height: 26 }} />
              </div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>Ошибка подтверждения</div>
            </div>
            <p className="auth-sub" style={{ marginBottom: 22 }}>{errorMsg}</p>
            <Link href="/login" className="btn btn-secondary btn-block btn-lg">
              Вернуться ко входу
            </Link>
          </>
        )}
      </div>
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmailInner />
    </Suspense>
  )
}
