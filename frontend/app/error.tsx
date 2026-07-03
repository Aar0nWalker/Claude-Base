'use client'
import { useEffect, useState } from 'react'
import { isChunkLoadError, recoverFromChunkError } from '@/lib/chunk-recovery'

export default function Error({
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
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="spinner" />
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      textAlign: 'center',
      padding: 24,
    }}>
      <div style={{ fontSize: 48, opacity: 0.15 }}>⚠</div>
      <h2 style={{ fontSize: 20, margin: 0 }}>Что-то пошло не так</h2>
      <p style={{ color: 'var(--fg-3)', margin: 0, fontSize: 14 }}>
        {error.message || 'Неизвестная ошибка'}
      </p>
      <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={reset}>
        Попробовать снова
      </button>
    </div>
  )
}
