import { AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { BookOpen, Info } from 'lucide-react'
import { ScrollArea } from '@/shared/components/ui/scroll-area'
import { Skeleton } from '@/shared/components/ui/skeleton'
import { SourceCard } from '@/features/documents/components/SourceCard'
import { useChatStore } from '@/features/chat/stores/chat-store'

function EmptySourceState() {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 py-10">
      <div className="h-12 w-12 rounded-xl bg-elevated border border-border flex items-center justify-center mb-3">
        <BookOpen className="size-5 text-text-tertiary" />
      </div>
      <p className="text-sm font-medium text-text-secondary mb-1">{t('dashboard.sources.empty')}</p>
      <p className="text-xs text-text-tertiary">
        {t('dashboard.sources.emptyBody')}
      </p>
    </div>
  )
}

export function RightPanel() {
  const { t } = useTranslation()
  const { sourcePanelChunks, isStreaming } = useChatStore()

  return (
    <aside className="flex flex-col h-full w-[300px] shrink-0 bg-base border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <BookOpen className="size-3.5 text-text-tertiary" />
          <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">{t('dashboard.sources.title')}</span>
        </div>
        {sourcePanelChunks.length > 0 && (
          <span className="text-[10px] text-text-tertiary bg-elevated px-1.5 py-0.5 rounded">
            {sourcePanelChunks.length}
          </span>
        )}
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-2">
          {isStreaming && sourcePanelChunks.length === 0 ? (
            <>
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-28 w-full" />
            </>
          ) : sourcePanelChunks.length === 0 ? (
            <EmptySourceState />
          ) : (
            <AnimatePresence initial={false}>
              {sourcePanelChunks.map((chunk, i) => (
                <SourceCard key={chunk.id} chunk={chunk} index={i} />
              ))}
            </AnimatePresence>
          )}
        </div>
      </ScrollArea>

      {/* Footer hint */}
      {sourcePanelChunks.length > 0 && (
        <div className="px-4 py-3 border-t border-border-subtle">
          <p className="flex items-start gap-1.5 text-[10px] text-text-tertiary">
            <Info className="size-3 shrink-0 mt-px" />
            {t('dashboard.sources.relevanceHint')}
          </p>
        </div>
      )}
    </aside>
  )
}
