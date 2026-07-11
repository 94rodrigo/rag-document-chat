import { useRef, useEffect, KeyboardEvent } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { ArrowUp, Square } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/components/ui/tooltip'

interface QueryBoxProps {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  onAbort?: () => void
  isStreaming: boolean
  disabled?: boolean
  placeholder?: string
}

export function QueryBox({
  value,
  onChange,
  onSubmit,
  onAbort,
  isStreaming,
  disabled,
  placeholder,
}: QueryBoxProps) {
  const { t } = useTranslation()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`
  }, [value])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isStreaming && value.trim()) onSubmit()
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="relative flex items-end gap-2 rounded-xl border border-border bg-surface px-4 py-3 shadow-sm focus-within:border-accent/40 focus-within:shadow-[0_0_0_3px_hsl(var(--accent)/0.08)] transition-all duration-150"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? t('chat.queryBox.placeholder')}
        disabled={disabled}
        rows={1}
        className={`flex-1 resize-none bg-transparent text-sm text-text-primary placeholder:text-text-tertiary outline-none leading-relaxed min-h-[28px] max-h-[160px] ${
          disabled ? 'opacity-50 cursor-not-allowed' : ''
        }`}
        aria-label={t('chat.queryBox.messageInput')}
      />

      {/* Submit / abort */}
      {isStreaming ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              size="icon-sm"
              variant="outline"
              onClick={onAbort}
              className="shrink-0 border-destructive/30 text-destructive hover:bg-destructive/10"
            >
              <Square className="size-3.5 fill-current" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('chat.queryBox.stopGeneration')}</TooltipContent>
        </Tooltip>
      ) : (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              size="icon-sm"
              onClick={onSubmit}
              disabled={!value.trim() || disabled}
              className="shrink-0"
            >
              <ArrowUp className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('chat.queryBox.send')}</TooltipContent>
        </Tooltip>
      )}
    </motion.div>
  )
}
