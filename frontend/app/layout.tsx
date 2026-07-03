import type { Metadata } from 'next'
import './globals.css'
import Providers from '@/components/providers'

export const metadata: Metadata = {
  metadataBase: new URL('https://{{DOMAIN}}'),
  title: '{{PROJECT_NAME}} — {{PROJECT_TAGLINE}}',
  description: '{{PROJECT_TAGLINE}}',
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    url: 'https://{{DOMAIN}}',
    siteName: '{{PROJECT_NAME}}',
    title: '{{PROJECT_NAME}} — {{PROJECT_TAGLINE}}',
    description: '{{PROJECT_TAGLINE}}',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){try{var t=localStorage.getItem('theme')||'dark';document.documentElement.setAttribute('data-theme',t)}catch(e){document.documentElement.setAttribute('data-theme','dark')}})()
        ` }} />
      </head>
      <body><Providers>{children}</Providers></body>
    </html>
  )
}
