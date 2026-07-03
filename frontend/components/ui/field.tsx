'use client'
import { useState } from 'react'
import Icon from '@/components/icon'

interface FieldProps {
  label?: string
  type?: string
  placeholder?: string
  value?: string
  onChange?: (value: string) => void
  autoFocus?: boolean
}

export default function Field({ label, type = 'text', placeholder, value, onChange, autoFocus }: FieldProps) {
  const isPassword = type === 'password'
  const [show, setShow] = useState(false)

  return (
    <div>
      {label && <label className="field-label">{label}</label>}
      <div style={{ position: 'relative' }}>
        <input
          className="field"
          type={isPassword && show ? 'text' : type}
          placeholder={placeholder}
          value={value}
          autoFocus={autoFocus}
          style={isPassword ? { paddingRight: 44 } : undefined}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow(s => !s)}
            title={show ? 'Скрыть пароль' : 'Показать пароль'}
            style={{
              position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', padding: 4,
              display: 'flex', alignItems: 'center', color: 'var(--fg-3)',
            }}
          >
            <Icon name={show ? 'eye-off' : 'eye'} style={{ width: 18, height: 18 }} />
          </button>
        )}
      </div>
    </div>
  )
}
