import Link from 'next/link'

export default function NotFound() {
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
      <div style={{ fontSize: 96, fontWeight: 800, lineHeight: 1, opacity: 0.08, userSelect: 'none' }}>404</div>
      <h1 style={{ fontSize: 22, margin: 0, marginTop: -8 }}>Страница не найдена</h1>
      <p style={{ color: 'var(--fg-3)', margin: 0, fontSize: 14 }}>
        Ссылка устарела или такой страницы не существует.
      </p>
      <Link href="/" className="btn btn-primary" style={{ marginTop: 8 }}>
        На главную
      </Link>
    </div>
  )
}
