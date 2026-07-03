'use client'
import { useEffect, useState } from 'react'
import Icon from '@/components/icon'
import { apiFetch } from '@/lib/api'
import { parseUtcDate } from '@/lib/data'

type Tab = 'prompts' | 'settings' | 'users' | 'errors'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'prompts', label: 'Промпты', icon: 'type' },
  { id: 'settings', label: 'Настройки', icon: 'sliders-horizontal' },
  { id: 'users', label: 'Пользователи', icon: 'users-round' },
  { id: 'errors', label: 'Ошибки', icon: 'alert-circle' },
]

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('prompts')

  return (
    <div className="content-in adm">
      <nav className="adm-nav">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            className={`adm-nav-item${tab === t.id ? ' active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            <Icon name={t.icon} className="ic" />
            {t.label}
          </button>
        ))}
      </nav>
      <div className="adm-content">
        {tab === 'prompts' && <PromptsTab />}
        {tab === 'settings' && <SettingsTab />}
        {tab === 'users' && <UsersTab />}
        {tab === 'errors' && <ErrorsTab />}
      </div>
    </div>
  )
}

// ---- Prompts ---- (backend keys by `key`, not id)

interface SystemPrompt {
  key: string
  label: string
  content: string
  updated_at?: string
}

function PromptsTab() {
  const [items, setItems] = useState<SystemPrompt[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)

  function load() {
    setLoading(true)
    apiFetch<SystemPrompt[]>('/backend/admin/prompts', { silent: true })
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function save(key: string) {
    setSaving(true)
    try {
      await apiFetch(`/backend/admin/prompts/${encodeURIComponent(key)}`, { method: 'PUT', json: { content: draft }, silent: true })
      setItems(items.map(p => (p.key === key ? { ...p, content: draft } : p)))
      setEditing(null)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="adm-sec-head">
        <h3>Системные промпты</h3>
      </div>
      {loading && <div className="empty">Загрузка…</div>}
      {!loading && items.length === 0 && <div className="empty">Промптов пока нет</div>}
      {items.map(p => (
        <div key={p.key} className="card" style={{ marginBottom: 12 }}>
          <div className="adm-row">
            <strong>{p.label || p.key}</strong>
            {p.updated_at && <span style={{ fontSize: 12, color: 'var(--fg-3)' }}>{parseUtcDate(p.updated_at).toLocaleString('ru-RU')}</span>}
          </div>
          {editing === p.key ? (
            <>
              <textarea
                className="field"
                value={draft}
                onChange={e => setDraft(e.target.value)}
                rows={8}
                style={{ resize: 'vertical', marginTop: 10 }}
              />
              <div className="adm-row-actions">
                <button className="btn btn-primary" disabled={saving} onClick={() => save(p.key)}>
                  {saving ? 'Сохранение…' : 'Сохранить'}
                </button>
                <button className="btn btn-ghost" onClick={() => setEditing(null)}>Отмена</button>
              </div>
            </>
          ) : (
            <>
              <p style={{ fontSize: 13, color: 'var(--fg-2)', marginTop: 8, whiteSpace: 'pre-wrap' }}>
                {p.content.length > 240 ? p.content.slice(0, 240) + '…' : p.content}
              </p>
              <div className="adm-row-actions">
                <button className="btn btn-ghost" onClick={() => { setEditing(p.key); setDraft(p.content) }}>
                  Редактировать
                </button>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  )
}

// ---- Settings ---- (registration_open: closed only when value === "0")

interface AppSetting {
  key: string
  value: string
}

function SettingsTab() {
  const [items, setItems] = useState<AppSetting[]>([])
  const [loading, setLoading] = useState(true)
  const [savingKey, setSavingKey] = useState<string | null>(null)

  function load() {
    setLoading(true)
    apiFetch<AppSetting[]>('/backend/admin/settings', { silent: true })
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function update(key: string, value: string) {
    setSavingKey(key)
    try {
      await apiFetch(`/backend/admin/settings/${encodeURIComponent(key)}`, { method: 'PUT', json: { value }, silent: true })
      setItems(items.map(s => (s.key === key ? { ...s, value } : s)))
    } finally {
      setSavingKey(null)
    }
  }

  const registrationOpen = items.find(s => s.key === 'registration_open')
  const regIsOpen = registrationOpen ? registrationOpen.value !== '0' : true

  return (
    <div>
      <div className="adm-sec-head">
        <h3>Настройки приложения</h3>
      </div>
      {loading && <div className="empty">Загрузка…</div>}

      {registrationOpen && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="adm-row">
            <div>
              <strong>Регистрация открыта</strong>
              <p style={{ fontSize: 12.5, color: 'var(--fg-3)', marginTop: 4 }}>
                Разрешить новым пользователям регистрироваться (иначе — в лист ожидания).
              </p>
            </div>
            <button
              className={`btn ${regIsOpen ? 'btn-primary' : 'btn-ghost'}`}
              disabled={savingKey === 'registration_open'}
              onClick={() => update('registration_open', regIsOpen ? '0' : '1')}
            >
              {regIsOpen ? 'Открыта' : 'Закрыта'}
            </button>
          </div>
        </div>
      )}

      {!loading && items.filter(s => s.key !== 'registration_open').map(s => (
        <div key={s.key} className="card" style={{ marginBottom: 12 }}>
          <div className="kv">
            <span className="k">{s.key}</span>
            <input
              className="field"
              style={{ maxWidth: 260 }}
              defaultValue={s.value}
              disabled={savingKey === s.key}
              onBlur={e => { if (e.target.value !== s.value) update(s.key, e.target.value) }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

// ---- Users ---- (backend: ?email&page → {users,total,page_size}; actions by email)

interface AdminUser {
  id: number
  email: string
  email_verified: boolean
  waitlisted: boolean
  created_at?: string
}

const USERS_PAGE_SIZE = 10

function UsersTab() {
  const [items, setItems] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page) })
    if (query.trim()) params.set('email', query.trim())
    apiFetch<{ users: AdminUser[]; total: number }>(`/backend/admin/users?${params}`, { silent: true })
      .then(res => { setItems(res.users); setTotal(res.total) })
      .catch(() => { setItems([]); setTotal(0) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [page])

  async function verify(email: string) {
    await apiFetch('/backend/admin/users/verify', { method: 'POST', json: { email }, silent: true })
    setItems(items.map(u => (u.email === email ? { ...u, email_verified: true } : u)))
  }

  async function approve(email: string) {
    await apiFetch('/backend/admin/users/approve', { method: 'POST', json: { email }, silent: true })
    setItems(items.map(u => (u.email === email ? { ...u, waitlisted: false } : u)))
  }

  async function sendResetLink(email: string) {
    await apiFetch('/backend/admin/users/reset-link', { method: 'POST', json: { email }, silent: true })
  }

  return (
    <div>
      <div className="adm-sec-head">
        <h3>Пользователи</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="field"
            placeholder="Поиск по email"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { setPage(1); load() } }}
          />
          <button className="btn btn-ghost" onClick={() => { setPage(1); load() }}>Найти</button>
        </div>
      </div>
      {loading && <div className="empty">Загрузка…</div>}
      {!loading && items.length === 0 && <div className="empty">Пользователи не найдены</div>}
      {items.map(u => (
        <div key={u.id} className="card" style={{ marginBottom: 10 }}>
          <div className="adm-row">
            <div>
              <strong>{u.email}</strong>
              <div className="adm-chips" style={{ marginTop: 6 }}>
                <span className="adm-chip">{u.email_verified ? 'подтверждён' : 'не подтверждён'}</span>
                {u.waitlisted && <span className="adm-chip">лист ожидания</span>}
              </div>
            </div>
            <div className="adm-row-actions">
              {u.waitlisted && (
                <button className="btn btn-ghost" onClick={() => approve(u.email)}>Одобрить</button>
              )}
              {!u.email_verified && (
                <button className="btn btn-ghost" onClick={() => verify(u.email)}>Подтвердить</button>
              )}
              <button className="btn btn-ghost" onClick={() => sendResetLink(u.email)}>Ссылка сброса пароля</button>
            </div>
          </div>
        </div>
      ))}
      {total > USERS_PAGE_SIZE && (
        <div className="adm-row-actions" style={{ justifyContent: 'center', marginTop: 12 }}>
          <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Назад</button>
          <span style={{ fontSize: 13, color: 'var(--fg-3)' }}>Стр. {page} из {Math.ceil(total / USERS_PAGE_SIZE)}</span>
          <button className="btn btn-ghost" disabled={page * USERS_PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Вперёд →</button>
        </div>
      )}
    </div>
  )
}

// ---- Errors ----

interface ErrorLogEntry {
  id: number
  message: string
  traceback?: string
  path?: string
  status?: number
  created_at?: string
}

function ErrorsTab() {
  const [items, setItems] = useState<ErrorLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)

  function load() {
    setLoading(true)
    apiFetch<ErrorLogEntry[]>('/backend/admin/errors', { silent: true })
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function clearAll() {
    await apiFetch('/backend/admin/errors', { method: 'DELETE', silent: true })
    setItems([])
  }

  return (
    <div>
      <div className="adm-sec-head">
        <h3>Лог ошибок</h3>
        {items.length > 0 && (
          <button className="btn btn-ghost" onClick={clearAll}>Очистить</button>
        )}
      </div>
      {loading && <div className="empty">Загрузка…</div>}
      {!loading && items.length === 0 && <div className="empty">Ошибок нет</div>}
      {items.map(e => (
        <div key={e.id} className="card" style={{ marginBottom: 10 }}>
          <div className="adm-row" style={{ cursor: 'pointer' }} onClick={() => setExpanded(expanded === e.id ? null : e.id)}>
            <div>
              <strong style={{ fontSize: 13 }}>{e.message}</strong>
              {e.created_at && <div style={{ fontSize: 12, color: 'var(--fg-3)', marginTop: 4 }}>{parseUtcDate(e.created_at).toLocaleString('ru-RU')}</div>}
            </div>
            <Icon name={expanded === e.id ? 'chevron-right' : 'chevron-down'} className="ic" />
          </div>
          {expanded === e.id && e.traceback && (
            <pre style={{ fontSize: 11.5, color: 'var(--fg-3)', marginTop: 10, whiteSpace: 'pre-wrap', overflowX: 'auto' }}>
              {e.traceback}
            </pre>
          )}
        </div>
      ))}
    </div>
  )
}
