'use client'
import Topbar from './topbar'

export default function ClientShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <Topbar />
      <div className="content">
        {children}
      </div>
    </div>
  )
}
