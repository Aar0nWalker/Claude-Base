'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { isChunkLoadError, recoverFromChunkError } from '@/lib/chunk-recovery'

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  // Stale chunk after a deploy → reload onto the new build instead of erroring.
  const [recovering, setRecovering] = useState(() => isChunkLoadError(error))
  useEffect(() => {
    if (isChunkLoadError(error)) {
      if (recoverFromChunkError()) return
      setRecovering(false)
    }
    console.error(error)
  }, [error])

  if (recovering) {
    return (
      <div className="content-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
        <div className="spinner" />
      </div>
    )
  }

  return (
    <div className="content-in" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 400,
      gap: 12,
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 40, opacity: 0.15 }}>⚠</div>
      <h2 style={{ fontSize: 18, margin: 0 }}>Ошибка загрузки</h2>
      <p style={{ color: 'var(--fg-3)', margin: 0, fontSize: 13 }}>
        {error.message || 'Неизвестная ошибка'}
      </p>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button className="btn btn-primary" onClick={reset}>Повторить</button>
        <Link href="/dashboard" className="btn btn-ghost">Дашборд</Link>
      </div>
    </div>
  )
}
