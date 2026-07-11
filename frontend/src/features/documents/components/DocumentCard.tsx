import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { FileText, Trash2, MessageSquare, Eye } from 'lucide-react'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { formatBytes, formatRelativeTime, getMimeTypeLabel } from '@/shared/lib/utils'
import { useCreateConversation } from '@/features/chat/hooks/use-chat'
import { DeleteDocumentDialog } from './DeleteDocumentDialog'
import type { Document } from '@/shared/types'

const statusVariant = {
  ready: 'success' as const,
  processing: 'warning' as const,
  uploading: 'secondary' as const,
  error: 'destructive' as const,
}

interface DocumentCardProps {
  doc: Document
  index: number
}

export function DocumentCard({ doc, index }: DocumentCardProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const createConversation = useCreateConversation()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const handleChat = (e: React.MouseEvent) => {
    e.stopPropagation()
    createConversation.mutate([doc.id])
    navigate('/dashboard')
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: index * 0.04 }}
        className="group rounded-lg border border-border bg-surface hover:border-accent/30 hover:bg-elevated/50 transition-all duration-150"
      >
        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0 mt-0.5">
              <FileText className="size-5 text-accent" />
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-text-primary truncate mb-1">{doc.name}</h3>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-[10px]">
                  {getMimeTypeLabel(doc.mimeType)}
                </Badge>
                <Badge variant={statusVariant[doc.status]} className="text-[10px]">
                  {doc.status === 'processing' && (
                    <span className="mr-1 h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse inline-block" />
                  )}
                  {t(`documents.status.${doc.status}`)}
                </Badge>
              </div>
              <div className="flex items-center gap-3 mt-1.5 text-[11px] text-text-tertiary">
                <span>{formatBytes(doc.sizeBytes)}</span>
                {doc.pageCount && <span>{t('documents.pages', { count: doc.pageCount })}</span>}
                <span>{formatRelativeTime(doc.createdAt)}</span>
              </div>
            </div>
          </div>

          {/* Action row */}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border/50">
            <Button
              size="sm"
              className="flex-1 h-7 text-xs"
              disabled={doc.status !== 'ready'}
              onClick={handleChat}
            >
              <MessageSquare className="size-3" />
              {t('documents.askQuestions')}
            </Button>
            <Button
              size="icon-sm"
              variant="ghost"
              className="h-7 w-7 text-text-tertiary hover:text-text-primary"
              onClick={() => navigate(`/documents/${doc.id}`)}
              title={t('documents.viewDocument')}
            >
              <Eye className="size-3.5" />
            </Button>
            <Button
              size="icon-sm"
              variant="ghost"
              className="h-7 w-7 text-text-tertiary hover:text-destructive hover:bg-destructive/10"
              onClick={() => setDeleteOpen(true)}
              title={t('documents.deleteDocument')}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        </div>
      </motion.div>

      <DeleteDocumentDialog
        document={doc}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
      />
    </>
  )
}
