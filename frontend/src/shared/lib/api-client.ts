import type {
  AuthTokens,
  ChatMessage,
  Citation,
  Conversation,
  Document,
  DocumentChunk,
  PaginatedResponse,
  Plan,
  StreamChunk,
  Subscription,
  UsageStats,
  User,
} from '@/shared/types'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1'

// ─── Token management ────────────────────────────────────────────────────────

let accessToken: string | null = localStorage.getItem('access_token')
let refreshPromise: Promise<void> | null = null

export function setTokens(tokens: AuthTokens) {
  accessToken = tokens.accessToken
  localStorage.setItem('access_token', tokens.accessToken)
  localStorage.setItem('refresh_token', tokens.refreshToken)
}

export function clearTokens() {
  accessToken = null
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

function redirectToLogin() {
  clearTokens()
  window.location.href = '/login'
}

// Exchanges the refresh token for a new access/refresh pair. The backend rotates
// refresh tokens (single-use — the old one is revoked when a new one is issued),
// so concurrent 401s must share one in-flight refresh instead of each firing their
// own request, which would race and invalidate each other.
function refreshAccessToken(): Promise<void> {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const storedRefreshToken = localStorage.getItem('refresh_token')
    if (!storedRefreshToken) throw new Error('No refresh token available')

    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: storedRefreshToken }),
    })

    if (!res.ok) throw new Error('Refresh token invalid or expired')

    setTokens(transformKeys(await res.json()) as AuthTokens)
  })().finally(() => {
    refreshPromise = null
  })

  return refreshPromise
}

// 401 here means "wrong credentials", not "expired session" — must never trigger
// the refresh/redirect flow.
const UNAUTHENTICATED_ENDPOINTS = new Set(['/auth/login', '/auth/register'])

// ─── snake_case → camelCase transformer ──────────────────────────────────────

function toCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, l: string) => l.toUpperCase())
}

function transformKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(transformKeys)
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        toCamel(k),
        transformKeys(v),
      ]),
    )
  }
  return value
}

function toSnake(s: string): string {
  return s.replace(/[A-Z]/g, (l) => `_${l.toLowerCase()}`)
}

// Only shallow — request bodies here are flat key/value objects, not nested.
function toSnakeKeys(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(value).map(([k, v]) => [toSnake(k), v]))
}

// ─── Base fetch ──────────────────────────────────────────────────────────────

async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    if (res.status === 401 && !isRetry && !UNAUTHENTICATED_ENDPOINTS.has(path)) {
      try {
        await refreshAccessToken()
        return request<T>(path, options, true)
      } catch {
        redirectToLogin()
        throw { message: 'Session expired', statusCode: 401 }
      }
    }

    let errorBody: { message?: string; statusCode?: number }
    try {
      errorBody = transformKeys(await res.json()) as typeof errorBody
    } catch {
      errorBody = { message: res.statusText, statusCode: res.status }
    }

    throw { ...errorBody, statusCode: res.status }
  }

  if (res.status === 204) return undefined as T
  // Transform all snake_case keys to camelCase before returning
  return transformKeys(await res.json()) as T
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    request<{ user: User; tokens: AuthTokens }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (name: string, email: string, password: string) =>
    request<{ user: User; tokens: AuthTokens }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    }),

  logout: () => request<void>('/auth/logout', { method: 'POST' }),

  me: () => request<User>('/auth/me'),

  refreshToken: (refreshToken: string) =>
    request<AuthTokens>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
}

// ─── Documents ───────────────────────────────────────────────────────────────

export const documentsApi = {
  list: (page = 1, perPage = 20) =>
    request<PaginatedResponse<Document>>(`/documents?page=${page}&per_page=${perPage}`),

  get: (id: string) => request<Document>(`/documents/${id}`),

  upload: (file: File, onProgress?: (pct: number) => void) => {
    const attempt = () =>
      new Promise<{ document: Document; taskId: string }>((resolve, reject) => {
        const formData = new FormData()
        formData.append('file', file)

        const xhr = new XMLHttpRequest()
        xhr.open('POST', `${BASE_URL}/documents`)
        if (accessToken) xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`)

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) onProgress?.((e.loaded / e.total) * 100)
        }

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(transformKeys(JSON.parse(xhr.responseText)) as { document: Document; taskId: string })
          } else if (xhr.status === 401) {
            reject({ status: 401 })
          } else {
            reject(transformKeys(JSON.parse(xhr.responseText)))
          }
        }

        xhr.onerror = () => reject({ message: 'Network error', statusCode: 0 })
        xhr.send(formData)
      })

    return attempt().catch(async (err) => {
      if (err?.status !== 401) throw err
      try {
        await refreshAccessToken()
      } catch {
        redirectToLogin()
        throw { message: 'Session expired', statusCode: 401 }
      }
      return attempt()
    })
  },

  delete: (id: string) => request<void>(`/documents/${id}`, { method: 'DELETE' }),

  getChunks: (id: string) => request<DocumentChunk[]>(`/documents/${id}/chunks`),

  search: (query: string) =>
    request<DocumentChunk[]>(`/documents/search?q=${encodeURIComponent(query)}`),
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export const chatApi = {
  listConversations: () => request<Conversation[]>('/conversations'),

  getConversation: (id: string) => request<Conversation>(`/conversations/${id}`),

  createConversation: (documentIds: string[]) =>
    request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ document_ids: documentIds }),
    }),

  deleteConversation: (id: string) =>
    request<void>(`/conversations/${id}`, { method: 'DELETE' }),

  getMessages: (conversationId: string) =>
    request<Conversation & { messages: ChatMessage[] }>(`/conversations/${conversationId}`)
      .then((conv) => conv.messages ?? []),

  deleteMessage: (conversationId: string, messageId: string, cascade = false) =>
    request<void>(`/conversations/${conversationId}/messages/${messageId}?cascade=${cascade}`, {
      method: 'DELETE',
    }),

  sendMessage: async (
    conversationId: string,
    content: string,
    onChunk: (chunk: StreamChunk) => void,
    signal?: AbortSignal,
  ): Promise<{ message: ChatMessage; citations: Citation[] }> => {
    const doFetch = () =>
      fetch(`${BASE_URL}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({ content }),
        signal,
      })

    let res = await doFetch()

    if (res.status === 401) {
      try {
        await refreshAccessToken()
      } catch {
        redirectToLogin()
        throw { message: 'Session expired', statusCode: 401 }
      }
      res = await doFetch()
    }

    if (!res.ok || !res.body) {
      throw { message: 'Stream failed', statusCode: res.status }
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let finalMessage: ChatMessage | null = null
    const citations: Citation[] = []

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break

      const lines = decoder.decode(value).split('\n')
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') continue

        try {
          const chunk = transformKeys(JSON.parse(raw)) as StreamChunk
          onChunk(chunk)
          if (chunk.type === 'citation' && chunk.citation) {
            citations.push(chunk.citation)
          }
          if (chunk.type === 'done' && chunk.content) {
            finalMessage = transformKeys(JSON.parse(chunk.content)) as ChatMessage
          }
        } catch {
          // malformed chunk — skip
        }
      }
    }

    return { message: finalMessage!, citations }
  },
}

// ─── Billing ─────────────────────────────────────────────────────────────────

export const billingApi = {
  getPlans: () => request<Plan[]>('/billing/plans'),

  getSubscription: () => request<Subscription | null>('/billing/subscription'),

  getUsage: () => request<UsageStats>('/billing/usage'),

  createCheckout: (planId: string) =>
    request<{ url: string }>('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
    }),

  cancelSubscription: () =>
    request<Subscription>('/billing/subscription/cancel', { method: 'POST' }),

  getPortalUrl: () => request<{ url: string }>('/billing/portal'),
}

// ─── Users ───────────────────────────────────────────────────────────────────

export const usersApi = {
  updateProfile: (data: Partial<Pick<User,
    'name' | 'avatarUrl' | 'notifyDocumentProcessing' | 'notifyWeeklySummary' | 'notifyProductUpdates'
  >>) =>
    request<User>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(toSnakeKeys(data)),
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>('/users/me/password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),

  deleteAccount: () => request<void>('/users/me', { method: 'DELETE' }),
}
