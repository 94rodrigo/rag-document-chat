import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { cn } from '@/shared/lib/utils'
import type { DocumentChunk } from '@/shared/types'

interface SourceCardProps {
  chunk: DocumentChunk
  index: number
}

export function SourceCard({ chunk, index }: SourceCardProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()

  const scorePercent = Math.round(chunk.score * 100)
  const previewText = chunk.content.slice(0, 200)
  const hasMore = chunk.content.length > 200

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, delay: index * 0.06 }}
      className="rounded-lg border border-border bg-surface hover:border-accent/30 transition-colors group"
    >
      {/* Header */}
      <div className="flex items-start gap-2 p-3">
        <div className="h-6 w-6 rounded bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0 mt-0.5">
          <span className="text-[10px] font-mono font-medium text-accent">{index + 1}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-text-primary truncate leading-tight">
            {chunk.documentName}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            {chunk.pageNumber && (
              <Badge variant="secondary" className="text-[9px] px-1 py-0">
                p.{chunk.pageNumber}
              </Badge>
            )}
            <div className="flex items-center gap-1">
              <div className="h-1 w-12 rounded-full bg-elevated overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all', {
                    'bg-emerald-400': scorePercent >= 80,
                    'bg-amber-400': scorePercent >= 60 && scorePercent < 80,
                    'bg-red-400': scorePercent < 60,
                  })}
                  style={{ width: `${scorePercent}%` }}
                />
              </div>
              <span className="text-[10px] text-text-tertiary">{scorePercent}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-3 pb-2">
        <p className="text-[11px] text-text-secondary leading-relaxed font-mono">
          {expanded ? chunk.content : previewText}
          {!expanded && hasMore && (
            <span className="text-text-tertiary">…</span>
          )}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between px-3 pb-2.5 pt-1 border-t border-border-subtle">
        <button
          onClick={() => setExpanded((p) => !p)}
          className="inline-flex items-center gap-1 text-[10px] text-text-tertiary hover:text-text-secondary transition-colors"
          disabled={!hasMore}
        >
          {expanded ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
          {expanded ? t('documents.sourceCard.showLess') : t('documents.sourceCard.showMore')}
        </button>
        <Button
          size="sm"
          variant="ghost"
          className="h-6 text-[10px] gap-1 text-text-tertiary hover:text-accent"
          onClick={() => {
            const page = chunk.pageNumber ? `?page=${chunk.pageNumber}` : ''
            navigate(`/documents/${chunk.documentId}${page}`, { state: { snippet: chunk.content } })
          }}
        >
          <ExternalLink className="size-2.5" />
          {t('documents.sourceCard.open')}
        </Button>
      </div>
    </motion.div>
  )
}
