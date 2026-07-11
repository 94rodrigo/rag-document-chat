import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslation } from 'react-i18next'
import { type ChatMessage } from '@/shared/types'
import { Citations } from './Citations'
import { useAuthStore } from '@/shared/stores/auth-store'
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/components/ui/avatar'

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
  const { i18n } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const isUser = message.role === 'user'

  const initials = user?.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) ?? '?'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
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
        {isUser ? (
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

        <span className="text-[10px] text-text-tertiary px-1">
          {new Date(message.createdAt).toLocaleTimeString(i18n.language, {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </motion.div>
  )
}
