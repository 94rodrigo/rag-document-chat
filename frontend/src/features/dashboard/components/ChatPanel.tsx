import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslation } from 'react-i18next'
import { Sparkles, Upload, X, UserPen } from 'lucide-react'
import { ScrollArea } from '@/shared/components/ui/scroll-area'
import { Skeleton } from '@/shared/components/ui/skeleton'
import { MessageBubble } from '@/features/chat/components/MessageBubble'
import { QueryBox } from '@/features/chat/components/QueryBox'
import { useChatStore } from '@/features/chat/stores/chat-store'
import { useDocumentsStore } from '@/features/documents/stores/documents-store'
import { useAuthStore } from '@/shared/stores/auth-store'
import { useMessages } from '@/features/chat/hooks/use-chat'
import { useSendMessage } from '@/features/chat/hooks/use-chat'
import { useUploadDocument } from '@/features/documents/hooks/use-documents'
import { truncate } from '@/shared/lib/utils'

// ─── Profile completion banner ────────────────────────────────────────────────

const BANNER_KEY = 'profile-banner-dismissed'

function ProfileBanner() {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(() => localStorage.getItem(BANNER_KEY) !== 'true')

  const dismiss = () => {
    localStorage.setItem(BANNER_KEY, 'true')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="shrink-0 flex items-center gap-3 px-5 py-2.5 bg-accent/8 border-b border-accent/20"
    >
      <UserPen className="size-3.5 text-accent shrink-0" />
      <p className="flex-1 text-xs text-text-secondary">
        {t('dashboard.profileBanner.prefix')}{' '}
        <Link to="/settings" className="text-accent hover:underline font-medium">
          {t('dashboard.profileBanner.link')}
        </Link>{' '}
        {t('dashboard.profileBanner.suffix')}
      </p>
      <button
        onClick={dismiss}
        className="shrink-0 text-text-tertiary hover:text-text-secondary transition-colors"
        aria-label="Dismiss"
      >
        <X className="size-3.5" />
      </button>
    </motion.div>
  )
}

// ─── Streaming bubble ─────────────────────────────────────────────────────────

function StreamingBubble({ content }: { content: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="h-7 w-7 rounded-full bg-accent/15 border border-accent/30 flex items-center justify-center shrink-0 mt-0.5">
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/40 stroke-accent" strokeWidth="1.5" />
          <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <div className="max-w-[85%] rounded-xl rounded-tl-sm bg-elevated border border-border px-4 py-2.5 text-sm">
        <div className="prose-citenest">
          {content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          ) : (
            <span className="inline-flex gap-1 items-center text-text-tertiary text-xs">
              <Sparkles className="size-3 text-accent animate-pulse" />
              Thinking…
            </span>
          )}
          {content && <span className="typing-cursor" />}
        </div>
      </div>
    </motion.div>
  )
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({
  hasDocuments,
  onPromptSelect,
}: {
  hasDocuments: boolean
  onPromptSelect: (prompt: string) => void
}) {
  const { t } = useTranslation()
  const upload = useUploadDocument()
  const suggestedPrompts = t('dashboard.suggestedPrompts', { returnObjects: true }) as string[]

  if (!hasDocuments) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8 select-none">
        {/* Atmospheric glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-accent/[0.03] blur-3xl" />
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center"
        >
          {/* Icon */}
          <div className="relative mb-6">
            <div className="h-16 w-16 rounded-2xl bg-elevated border border-border flex items-center justify-center">
              <Upload className="size-6 text-text-tertiary" />
            </div>
          </div>

          <h3 className="font-display text-xl text-text-primary mb-2">
            {t('dashboard.emptyState.noDocuments.title')}
          </h3>
          <p className="text-sm text-text-secondary max-w-[280px] leading-relaxed mb-6">
            {t('dashboard.emptyState.noDocuments.body')}
          </p>

          {/* Upload CTA */}
          <label className="cursor-pointer">
            <input
              type="file"
              className="sr-only"
              accept=".pdf,.txt,.docx,.md"
              multiple
              onChange={(e) => {
                const files = Array.from(e.target.files ?? [])
                files.forEach((f) => upload.mutate(f))
                e.target.value = ''
              }}
            />
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent/10 border border-accent/20 text-sm text-accent hover:bg-accent/15 transition-colors">
              <Upload className="size-3.5" />
              {t('dashboard.emptyState.noDocuments.upload')}
            </div>
          </label>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="relative flex flex-col items-center justify-center h-full text-center px-8 select-none">
      {/* Atmospheric radial glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[400px] rounded-full bg-accent/[0.04] blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className="flex flex-col items-center relative"
      >
        {/* Icon */}
        <div className="h-14 w-14 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-5">
          <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/30 stroke-accent" strokeWidth="1.5" />
            <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="18" cy="18" r="4" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
            <path d="M16.5 18h3M18 16.5v3" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>

        <h3 className="font-display text-xl text-text-primary mb-2">
          {t('dashboard.emptyState.withDocuments.title')}
        </h3>
        <p className="text-sm text-text-secondary max-w-[300px] leading-relaxed mb-7">
          {t('dashboard.emptyState.withDocuments.body')}
        </p>

        {/* Suggested prompts */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-wrap gap-2 justify-center max-w-sm"
        >
          {suggestedPrompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onPromptSelect(prompt)}
              className="px-3 py-1.5 rounded-lg text-xs text-text-secondary border border-border bg-surface hover:bg-elevated hover:border-accent/30 hover:text-accent transition-all duration-150"
            >
              {prompt}
            </button>
          ))}
        </motion.div>
      </motion.div>
    </div>
  )
}

// ─── Conversation header ──────────────────────────────────────────────────────

function ConversationHeader({ title }: { title: string }) {
  return (
    <div className="shrink-0 flex items-center gap-3 px-6 py-3 border-b border-border-subtle">
      <div className="h-5 w-5 rounded bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
        <svg className="h-2.5 w-2.5" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/40 stroke-accent" strokeWidth="2" />
          <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </div>
      <span className="text-xs font-medium text-text-secondary truncate">
        {truncate(title, 60)}
      </span>
    </div>
  )
}

// ─── Chat panel ───────────────────────────────────────────────────────────────

export function ChatPanel() {
  const { t } = useTranslation()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const {
    activeConversationId,
    conversations,
    messages,
    isStreaming,
    streamingContent,
  } = useChatStore()

  const { documents } = useDocumentsStore()
  const hasDocuments = documents.length > 0
  const user = useAuthStore((s) => s.user)
  const showProfileBanner = user?.name === 'Your Name' || user?.name === ''

  const { sendMessage, abort } = useSendMessage()
  const { isLoading } = useMessages(activeConversationId)

  const currentMessages = activeConversationId
    ? (messages[activeConversationId] ?? [])
    : []

  const activeConversation = conversations.find((c) => c.id === activeConversationId)
  const showHeader =
    !!activeConversation &&
    activeConversation.title !== 'New conversation' &&
    currentMessages.length > 0

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentMessages.length, streamingContent])

  const handleSubmit = () => {
    if (!input.trim() || isStreaming) return
    sendMessage(input.trim())
    setInput('')
  }

  const handlePromptSelect = (prompt: string) => {
    setInput(prompt)
  }

  return (
    <div className="flex flex-col h-full min-h-0 bg-base">
      {/* Profile completion banner */}
      <AnimatePresence>
        {showProfileBanner && <ProfileBanner />}
      </AnimatePresence>

      {/* Conversation title header */}
      <AnimatePresence>
        {showHeader && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <ConversationHeader title={activeConversation.title} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="max-w-3xl mx-auto px-6 py-6 space-y-5">
          {isLoading ? (
            <>
              <Skeleton className="h-12 w-3/4 ml-auto" />
              <Skeleton className="h-16 w-2/3" />
              <Skeleton className="h-10 w-1/2 ml-auto" />
            </>
          ) : currentMessages.length === 0 && !isStreaming ? (
            <div className="h-[calc(100vh-220px)] flex items-center justify-center">
              <EmptyState
                hasDocuments={hasDocuments}
                onPromptSelect={handlePromptSelect}
              />
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {currentMessages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isStreaming && (
                <StreamingBubble key="streaming" content={streamingContent} />
              )}
            </AnimatePresence>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="shrink-0 px-6 pb-5 pt-3 border-t border-border-subtle">
        <div className="max-w-3xl mx-auto">
          <QueryBox
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            onAbort={abort}
            isStreaming={isStreaming}
            disabled={!activeConversationId}
            placeholder={
              activeConversationId
                ? t('dashboard.inputPlaceholder.withConversation')
                : t('dashboard.inputPlaceholder.noConversation')
            }
          />
          <p className="text-center text-[10px] text-text-tertiary mt-2">
            {t('dashboard.disclaimer')}
          </p>
        </div>
      </div>
    </div>
  )
}
