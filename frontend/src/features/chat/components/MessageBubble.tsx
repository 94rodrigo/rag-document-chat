import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Copy, Pencil, Trash2, Check, X } from 'lucide-react'
import { type ChatMessage } from '@/shared/types'
import { Citations } from './Citations'
import { useAuthStore } from '@/shared/stores/auth-store'
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/components/ui/avatar'
import { Button } from '@/shared/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/components/ui/tooltip'
import { useChatStore } from '../stores/chat-store'
import { useSendMessage, useDeleteMessage } from '../hooks/use-chat'

interface MessageBubbleProps {
  message: ChatMessage
}

function DocnaAvatar() {
  return (
    <div className="h-7 w-7 rounded-full bg-accent/15 border border-accent/30 flex items-center justify-center shrink-0">
      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/40 stroke-accent" strokeWidth="1.5" />
        <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    </div>
  )
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { t, i18n } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const { editMessage } = useSendMessage()
  const deleteMessage = useDeleteMessage()
  const isUser = message.role === 'user'

  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(message.content)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!isEditing) return
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 240)}px`
    ta.focus()
    ta.setSelectionRange(ta.value.length, ta.value.length)
  }, [isEditing, editValue])

  const initials = user?.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) ?? '?'

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    toast.success(t('chat.toasts.copied'))
  }

  const startEdit = () => {
    setEditValue(message.content)
    setIsEditing(true)
  }

  const cancelEdit = () => setIsEditing(false)

  const saveEdit = () => {
    if (!editValue.trim() || editValue === message.content) {
      setIsEditing(false)
      return
    }
    setIsEditing(false)
    editMessage(message.id, editValue.trim())
  }

  const actionsDisabled = isStreaming

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className={`group flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      {isUser ? (
        <Avatar className="h-7 w-7 shrink-0 mt-0.5">
          <AvatarImage src={user?.avatarUrl} />
          <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
        </Avatar>
      ) : (
        <div className="mt-0.5 shrink-0">
          <DocnaAvatar />
        </div>
      )}

      <div className={`flex flex-col gap-1.5 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        {isEditing ? (
          <div className="w-full min-w-[280px] rounded-xl border border-accent/40 bg-surface px-3 py-2 shadow-[0_0_0_3px_hsl(var(--accent)/0.08)]">
            <textarea
              ref={textareaRef}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  saveEdit()
                } else if (e.key === 'Escape') {
                  cancelEdit()
                }
              }}
              rows={1}
              className="w-full resize-none bg-transparent text-sm text-text-primary outline-none leading-relaxed min-h-[24px] max-h-[240px]"
            />
            <div className="flex items-center justify-end gap-1.5 mt-2">
              <Button variant="ghost" size="sm" onClick={cancelEdit} className="h-6 text-[11px] gap-1">
                <X className="size-3" />
                {t('chat.messageActions.cancel')}
              </Button>
              <Button size="sm" onClick={saveEdit} className="h-6 text-[11px] gap-1">
                <Check className="size-3" />
                {t('chat.messageActions.save')}
              </Button>
            </div>
          </div>
        ) : isUser ? (
          <div className="rounded-xl rounded-tr-sm bg-accent/15 border border-accent/20 px-4 py-2.5 text-sm text-text-primary">
            {message.content}
          </div>
        ) : (
          <div className="rounded-xl rounded-tl-sm bg-elevated border border-border px-4 py-2.5 text-sm">
            <div className="prose-docna">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
            {message.citations && message.citations.length > 0 && (
              <Citations citations={message.citations} />
            )}
          </div>
        )}

        {!isEditing && (
          <div className="flex items-center gap-1.5 px-1">
            <span className="text-[10px] text-text-tertiary">
              {new Date(message.createdAt).toLocaleTimeString(i18n.language, {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>

            {/* Actions — revealed on row hover */}
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleCopy}
                    aria-label={t('chat.messageActions.copy')}
                    className="h-5 w-5 rounded flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-elevated transition-colors"
                  >
                    <Copy className="size-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>{t('chat.messageActions.copy')}</TooltipContent>
              </Tooltip>

              {isUser && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={startEdit}
                      disabled={actionsDisabled}
                      aria-label={t('chat.messageActions.edit')}
                      className="h-5 w-5 rounded flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-elevated transition-colors disabled:opacity-40 disabled:pointer-events-none"
                    >
                      <Pencil className="size-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{t('chat.messageActions.edit')}</TooltipContent>
                </Tooltip>
              )}

              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => deleteMessage.mutate(message.id)}
                    disabled={actionsDisabled}
                    aria-label={t('chat.messageActions.delete')}
                    className="h-5 w-5 rounded flex items-center justify-center text-text-tertiary hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-40 disabled:pointer-events-none"
                  >
                    <Trash2 className="size-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>{t('chat.messageActions.delete')}</TooltipContent>
              </Tooltip>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
