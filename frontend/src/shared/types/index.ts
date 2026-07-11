// ─── Auth ────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  name: string
  avatarUrl?: string
  plan: 'free' | 'pro' | 'enterprise'
  notifyDocumentProcessing: boolean
  notifyWeeklySummary: boolean
  notifyProductUpdates: boolean
  createdAt: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  expiresIn: number   // seconds until expiry (from backend expires_in)
  tokenType: string
}

// ─── Documents ───────────────────────────────────────────────────────────────

export type DocumentStatus = 'uploading' | 'processing' | 'ready' | 'error'

export interface Document {
  id: string
  name: string
  mimeType: string
  sizeBytes: number
  pageCount?: number
  status: DocumentStatus
  createdAt: string
  processedAt?: string
  errorMessage?: string
}

export interface DocumentChunk {
  id: string
  documentId: string
  documentName: string
  content: string
  pageNumber?: number
  score: number
  metadata: Record<string, unknown>
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export interface Citation {
  chunkId: string
  documentId: string
  documentName: string
  pageNumber?: number
  content: string
  score: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  createdAt: string
  isStreaming?: boolean
}

export interface Conversation {
  id: string
  title: string
  documentIds: string[]
  createdAt: string
  updatedAt: string
  messageCount: number
  lastMessage?: string
}

// ─── Billing ─────────────────────────────────────────────────────────────────

export interface Plan {
  id: string
  name: string
  price: number
  interval: 'month' | 'year'
  features: string[]
  limits: {
    documents: number
    queries: number
    storageGb: number
  }
}

export interface Subscription {
  id: string
  planId: string
  status: 'active' | 'canceled' | 'past_due' | 'trialing'
  currentPeriodEnd: string
  cancelAtPeriodEnd: boolean
}

export interface UsageStats {
  documentsUsed: number
  documentsLimit: number
  queriesUsed: number
  queriesLimit: number
  storageUsedBytes: number
  storageLimitBytes: number
}

// ─── API ─────────────────────────────────────────────────────────────────────

export interface ApiError {
  message: string
  code?: string
  statusCode: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  perPage: number
  hasMore: boolean
}

export interface ApiResponse<T> {
  data: T
  success: boolean
}

// ─── Stream ──────────────────────────────────────────────────────────────────

export interface StreamChunk {
  type: 'text' | 'citation' | 'done' | 'error'
  content?: string
  citation?: Citation
  error?: string
}
