import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import i18n from '@/shared/i18n'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

const relativeTimeFormatter = () => new Intl.RelativeTimeFormat(i18n.language, { numeric: 'auto' })

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return relativeTimeFormatter().format(0, 'second')
  if (diffMins < 60) return relativeTimeFormatter().format(-diffMins, 'minute')
  if (diffHours < 24) return relativeTimeFormatter().format(-diffHours, 'hour')
  if (diffDays < 7) return relativeTimeFormatter().format(-diffDays, 'day')
  return new Intl.DateTimeFormat(i18n.language, { month: 'short', day: 'numeric' }).format(date)
}

export function truncate(str: string, length: number): string {
  return str.length > length ? str.slice(0, length) + '…' : str
}

export function generateId(): string {
  return Math.random().toString(36).slice(2, 11)
}

export function getMimeTypeLabel(mimeType: string): string {
  const map: Record<string, string> = {
    'application/pdf': 'PDF',
    'text/plain': 'TXT',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
    'application/msword': 'DOC',
    'text/markdown': 'MD',
    'text/html': 'HTML',
  }
  return map[mimeType] ?? mimeType.split('/')[1]?.toUpperCase() ?? 'FILE'
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
