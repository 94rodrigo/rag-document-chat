import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FileText, Plus, Loader2, MessageSquare } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import { Badge } from '@/shared/components/ui/badge'
import { useCreateConversation } from '../hooks/use-chat'
import { getMimeTypeLabel } from '@/shared/lib/utils'
import type { Document } from '@/shared/types'

interface NewConversationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  documents: Document[]
}

export function NewConversationDialog({ open, onOpenChange, documents }: NewConversationDialogProps) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const createConversation = useCreateConversation()

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const toggleAll = () =>
    setSelected(selected.size === documents.length ? new Set() : new Set(documents.map((d) => d.id)))

  const handleStart = () => {
    if (selected.size === 0) return
    createConversation.mutate([...selected], {
      onSuccess: () => {
        setSelected(new Set())
        onOpenChange(false)
      },
    })
  }

  const handleOpenChange = (v: boolean) => {
    if (!createConversation.isPending) {
      if (!v) setSelected(new Set())
      onOpenChange(v)
    }
  }

  const readyDocs = documents.filter((d) => d.status === 'ready')

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="h-9 w-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
              <MessageSquare className="size-4 text-accent" />
            </div>
            <DialogTitle>{t('chat.newConversation.title')}</DialogTitle>
          </div>
          <DialogDescription>
            {t('chat.newConversation.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="mt-1 space-y-1 max-h-72 overflow-y-auto -mx-1 px-1">
          {readyDocs.length === 0 ? (
            <p className="text-xs text-text-tertiary text-center py-6">
              {t('chat.newConversation.noDocuments')}
            </p>
          ) : (
            <>
              {readyDocs.length > 1 && (
                <button
                  onClick={toggleAll}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs text-text-secondary hover:bg-elevated transition-colors mb-1"
                >
                  <div className={`h-3.5 w-3.5 rounded border flex items-center justify-center shrink-0 transition-colors ${
                    selected.size === readyDocs.length
                      ? 'bg-accent border-accent'
                      : selected.size > 0
                      ? 'bg-accent/40 border-accent'
                      : 'border-border'
                  }`}>
                    {selected.size > 0 && (
                      <svg viewBox="0 0 10 10" className="size-2 text-base fill-current">
                        {selected.size === readyDocs.length
                          ? <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                          : <path d="M2 5h6" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                        }
                      </svg>
                    )}
                  </div>
                  <span className="font-medium">
                    {selected.size === readyDocs.length ? t('chat.newConversation.deselectAll') : t('chat.newConversation.selectAll')}
                  </span>
                </button>
              )}

              {readyDocs.map((doc) => {
                const isSelected = selected.has(doc.id)
                return (
                  <button
                    key={doc.id}
                    onClick={() => toggle(doc.id)}
                    className={`w-full flex items-center gap-3 px-2 py-2 rounded-md border transition-colors text-left ${
                      isSelected
                        ? 'border-accent/40 bg-accent/5'
                        : 'border-transparent hover:bg-elevated'
                    }`}
                  >
                    <div className={`h-3.5 w-3.5 rounded border flex items-center justify-center shrink-0 transition-colors ${
                      isSelected ? 'bg-accent border-accent' : 'border-border'
                    }`}>
                      {isSelected && (
                        <svg viewBox="0 0 10 10" className="size-2">
                          <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                    </div>
                    <div className="h-7 w-7 rounded bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                      <FileText className="size-3.5 text-accent" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-text-primary truncate leading-tight">{doc.name}</p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Badge variant="secondary" className="text-[9px] px-1 py-0">
                          {getMimeTypeLabel(doc.mimeType)}
                        </Badge>
                      </div>
                    </div>
                  </button>
                )
              })}
            </>
          )}
        </div>

        <DialogFooter className="mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleOpenChange(false)}
            disabled={createConversation.isPending}
          >
            {t('common.cancel')}
          </Button>
          <Button
            size="sm"
            onClick={handleStart}
            disabled={selected.size === 0 || createConversation.isPending}
            className="gap-1.5"
          >
            {createConversation.isPending ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                {t('chat.newConversation.starting')}
              </>
            ) : (
              <>
                <Plus className="size-3.5" />
                {t('chat.newConversation.start')}
                {selected.size > 0 && (
                  <span className="ml-0.5 opacity-60">
                    ({selected.size})
                  </span>
                )}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
