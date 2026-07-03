'use client'
import Icon from '@/components/icon'

interface ChipOption<T = string | number> {
  value: T
  label: string
  icon?: string
  hint?: string
  disabled?: boolean
}

interface ChipsProps<T extends string | number> {
  options: ChipOption<T>[]
  value: T
  onChange: (value: T) => void
  cols?: number
}

export default function Chips<T extends string | number>({ options, value, onChange, cols }: ChipsProps<T>) {
  const gridStyle = cols
    ? { display: 'grid', gridTemplateColumns: `repeat(${cols},1fr)`, gap: 10 }
    : undefined
  return (
    <div className="chips" style={gridStyle}>
      {options.map((o) => (
        <button
          key={String(o.value)}
          className={`chip-opt${value === o.value ? ' active' : ''}${o.disabled ? ' disabled' : ''}`}
          disabled={o.disabled}
          onClick={() => !o.disabled && onChange(o.value)}
        >
          {o.icon && <Icon name={o.icon} className="ic" />}
          {o.label}
          {o.hint && (
            <span className="chip-hint">
              <span className="chip-hint-icon">ⓘ</span>
              <span className="chip-hint-popup">{o.hint}</span>
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
