import { type Citation } from '@/shared/types'
import { FileText, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface CitationsProps {
  citations: Citation[]
  onCitationClick?: (citation: Citation) => void
}

export function Citations({ citations, onCitationClick }: CitationsProps) {
  const navigate = useNavigate()

  if (!citations.length) return null

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {citations.map((c, i) => (
        <button
          key={c.chunkId}
          onClick={() => {
            onCitationClick?.(c)
            const page = c.pageNumber ? `?page=${c.pageNumber}` : ''
            navigate(`/documents/${c.documentId}${page}`, { state: { snippet: c.content } })
          }}
          className="inline-flex items-center gap-1.5 rounded border border-accent/25 bg-accent/8 px-2 py-1 text-[11px] text-accent hover:bg-accent/15 transition-colors"
          title={c.content.slice(0, 120) + '…'}
        >
          <FileText className="size-2.5 shrink-0" />
          <span className="max-w-[140px] truncate">{c.documentName}</span>
          {c.pageNumber && (
            <span className="text-accent/60">p.{c.pageNumber}</span>
          )}
          <span className="h-3.5 w-3.5 rounded-sm bg-accent/15 text-[9px] flex items-center justify-center font-mono">
            {i + 1}
          </span>
          <ExternalLink className="size-2.5 shrink-0 opacity-50" />
        </button>
      ))}
    </div>
  )
}
