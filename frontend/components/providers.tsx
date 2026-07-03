'use client'
import { AuthProvider } from '@/lib/auth-context'
import ToastProvider from '@/components/toast-provider'
import ConfirmProvider from '@/components/confirm-provider'
import { ReactNode, useEffect } from 'react'
import { installChunkErrorAutoReload } from '@/lib/chunk-recovery'

export default function Providers({ children }: { children: ReactNode }) {
  // Auto-reload onto the fresh build when a stale chunk fails after a deploy
  // (otherwise SPA navigation goes blank and in-progress state never re-attaches).
  useEffect(() => { installChunkErrorAutoReload() }, [])
  return (
    <ToastProvider>
      <ConfirmProvider>
        <AuthProvider>{children}</AuthProvider>
      </ConfirmProvider>
    </ToastProvider>
  )
}
