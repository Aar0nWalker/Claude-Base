// Central API client. Every call to /backend/* goes through apiFetch so that:
//  - httpOnly auth cookies are sent automatically,
//  - server errors are turned into one friendly message (never a raw traceback),
//  - that message is shown to the user via the global toast automatically,
//  - 401 triggers a single logout handler.
// Callers get parsed JSON on success or a thrown ApiError on failure.

let _sessionActive = false
export function setSessionActive(active: boolean) { _sessionActive = active }

type ToastFn = (msg: string) => void
let _errorToast: ToastFn | null = null
export function registerErrorToast(fn: ToastFn | null) { _errorToast = fn }

let _onUnauthorized: (() => void) | null = null
export function registerUnauthorized(fn: (() => void) | null) { _onUnauthorized = fn }

class ApiError extends Error {
  status: number
  detail: string
  constructor(message: string, status: number, detail: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

// Map an HTTP status (+ server detail) to a single human message.
function friendly(status: number, detail: string): string {
  switch (status) {
    case 0:   return 'Нет связи с сервером. Проверьте интернет и попробуйте снова.'
    case 401: return 'Сессия истекла — войдите снова.'
    case 402: return detail || 'Недостаточно средств.'
    case 403: return 'Недостаточно прав для этого действия.'
    case 404: return detail || 'Не найдено.'
    case 413: return 'Файл слишком большой.'
    case 422: return 'Проверьте введённые данные.'
    case 429: return detail || 'Слишком много запросов — подождите немного.'
    case 503: return detail || 'Сервис временно недоступен — попробуйте через минуту.'
  }
  if (status >= 500) return 'Что-то пошло не так. Мы уже знаем о проблеме, попробуйте позже.'
  return detail || 'Произошла ошибка. Попробуйте ещё раз.'
}

export interface ApiOptions extends RequestInit {
  /** Don't auto-show the global error toast (caller will handle the message). */
  silent?: boolean
  /** Parse a JSON body and set the Content-Type header automatically. */
  json?: unknown
}

export async function apiFetch<T = any>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { silent, json, headers, body, ...rest } = opts
  const h: Record<string, string> = { ...(headers as Record<string, string> | undefined) }

  let finalBody = body
  if (json !== undefined) {
    h['Content-Type'] = 'application/json'
    finalBody = JSON.stringify(json)
  }

  let res: Response
  try {
    res = await fetch(path, { ...rest, credentials: 'include', headers: h, body: finalBody })
  } catch {
    const msg = friendly(0, '')
    if (!silent) _errorToast?.(msg)
    throw new ApiError(msg, 0, '')
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({} as any))
    const detail = typeof data?.detail === 'string' ? data.detail : ''
    const msg = friendly(res.status, detail)
    // A truly expired session logs the user out, but login/register 401s
    // ("wrong password") happen before a session exists and should stay inline.
    if (res.status === 401 && _sessionActive) _onUnauthorized?.()
    if (!silent) _errorToast?.(msg)
    // silent callers render their own message → give them the precise server
    // text (e.g. "Неверный email или пароль", "email_not_verified"), not the
    // generic friendly line.
    throw new ApiError(silent && detail ? detail : msg, res.status, detail)
  }

  if (res.status === 204) return undefined as T
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json() as Promise<T>
  return (await res.text()) as unknown as T
}
