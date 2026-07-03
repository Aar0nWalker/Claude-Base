interface BadgeProps {
  kind?: 'neutral' | 'accent' | 'success' | 'warning'
  children: React.ReactNode
  dot?: string
}

export default function Badge({ kind = 'neutral', children, dot }: BadgeProps) {
  return (
    <span className={`badge badge-${kind}`}>
      {dot && <span className="dot" style={{ background: dot }} />}
      {children}
    </span>
  )
}
