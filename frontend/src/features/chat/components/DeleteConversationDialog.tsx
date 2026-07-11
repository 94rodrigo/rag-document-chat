import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Trash2, TriangleAlert, MessageSquare, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import { useDeleteConversation } from '../hooks/use-chat'
import type { Conversation } from '@/shared/types'

interface DeleteConversationDialogProps {
  conversation: Conversation
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DeleteConversationDialog({ conversation, open, onOpenChange }: DeleteConversationDialogProps) {
  const { t } = useTranslation()
  const deleteConv = useDeleteConversation()
  const [confirmed, setConfirmed] = useState(false)

  const handleDelete = () => {
    setConfirmed(true)
    deleteConv.mutate(conversation.id, {
      onSettled: () => {
        setConfirmed(false)
        onOpenChange(false)
      },
    })
  }

  const isPending = deleteConv.isPending || confirmed

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="h-9 w-9 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center justify-center shrink-0">
              <TriangleAlert className="size-4 text-destructive" />
            </div>
            <DialogTitle>{t('chat.deleteDialog.title')}</DialogTitle>
          </div>

          <div className="flex items-center gap-2.5 rounded-md bg-elevated border border-border px-3 py-2 mt-2">
            <div className="h-7 w-7 rounded bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
              <MessageSquare className="size-3.5 text-accent" />
            </div>
            <span className="text-xs font-medium text-text-primary truncate">{conversation.title}</span>
          </div>

          <DialogDescription className="mt-3">
            {t('chat.deleteDialog.body')}{' '}
            <span className="text-text-primary font-medium">{t('chat.deleteDialog.bodyEmphasis')}</span>
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            {t('common.cancel')}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={isPending}
            className="gap-1.5"
          >
            {isPending ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                {t('common.deleting')}
              </>
            ) : (
              <>
                <Trash2 className="size-3.5" />
                {t('common.delete')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
