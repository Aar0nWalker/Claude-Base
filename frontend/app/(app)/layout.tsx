import ClientShell from '@/components/layout/client-shell'
import ActionTracker from '@/components/action-tracker'
import '@/styles/app.css'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <ClientShell><ActionTracker />{children}</ClientShell>
}
