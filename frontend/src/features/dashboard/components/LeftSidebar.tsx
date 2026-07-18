import { Link, useNavigate } from 'react-router-dom'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Upload, FileText, MessageSquare, Settings, CreditCard,
  LayoutDashboard, Plus, MoreHorizontal, LogOut, User, Trash2, ChevronDown
} from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/shared/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/components/ui/avatar'
import { Badge } from '@/shared/components/ui/badge'
import { Progress } from '@/shared/components/ui/progress'
import { Separator } from '@/shared/components/ui/separator'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from '@/shared/components/ui/dropdown-menu'
import { ThemeToggle } from '@/shared/components/ThemeToggle'
import { LanguageSelector } from '@/shared/components/LanguageSelector'
import { useAuthStore } from '@/shared/stores/auth-store'
import { useDocumentsStore } from '@/features/documents/stores/documents-store'
import { useChatStore } from '@/features/chat/stores/chat-store'
import { useUploadDocument } from '@/features/documents/hooks/use-documents'
import { useCreateConversation } from '@/features/chat/hooks/use-chat'
import { DeleteDocumentDialog } from '@/features/documents/components/DeleteDocumentDialog'
import { DeleteConversationDialog } from '@/features/chat/components/DeleteConversationDialog'
import { NewConversationDialog } from '@/features/chat/components/NewConversationDialog'
import { useLogout } from '@/features/auth/hooks/use-auth'
import { formatRelativeTime, getMimeTypeLabel, formatBytes, truncate } from '@/shared/lib/utils'
import type { Document, Conversation } from '@/shared/types'

// ─── Logo ─────────────────────────────────────────────────────────────────────

function CitenestLogo() {
  return (
    <Link to="/dashboard" className="flex items-center gap-2 px-3 py-1 rounded hover:bg-elevated transition-colors">
      <svg className="h-6 w-6 shrink-0" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
        <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="18" cy="18" r="4" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
        <path d="M16.5 18h3M18 16.5v3" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <span className="font-display text-base text-text-primary tracking-tight">Citenest</span>
    </Link>
  )
}

// ─── Document item ────────────────────────────────────────────────────────────

function DocumentItem({ doc }: { doc: Document }) {
  const { t } = useTranslation()
  const createConversation = useCreateConversation()
  const navigate = useNavigate()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const handleClick = () => {
    createConversation.mutate([doc.id])
    navigate('/dashboard')
  }

  return (
    <>
      <div className="group flex items-center gap-1 rounded-md hover:bg-elevated transition-colors min-w-0 w-full">
        {/* Main row — takes all available space */}
        <div
          role="button"
          tabIndex={0}
          onClick={handleClick}
          onKeyDown={(e) => e.key === 'Enter' && handleClick()}
          className="flex-1 min-w-0 flex items-center gap-2 px-2 py-1.5 cursor-pointer"
        >
          <div className="h-7 w-7 rounded bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
            <FileText className="size-3.5 text-accent" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-text-primary truncate leading-tight">{doc.name}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Badge variant="secondary" className="text-[9px] px-1 py-0">
                {getMimeTypeLabel(doc.mimeType)}
              </Badge>
              <span className="text-[10px] text-text-tertiary">{formatBytes(doc.sizeBytes)}</span>
            </div>
          </div>
          {doc.status === 'processing' && (
            <div className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse shrink-0" />
          )}
          {doc.status === 'ready' && (
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
          )}
        </div>

        {/* Delete button — appears on row hover */}
        <button
          onClick={(e) => { e.stopPropagation(); setDeleteOpen(true) }}
          aria-label={t('sidebar.deleteDocumentAria', { name: doc.name })}
          className="shrink-0 mr-1.5 h-5 w-5 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 text-text-tertiary hover:text-destructive hover:bg-destructive/10 transition-all"
        >
          <Trash2 className="size-3" />
        </button>
      </div>

      <DeleteDocumentDialog
        document={doc}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
      />
    </>
  )
}

// ─── Conversation item ────────────────────────────────────────────────────────

function ConversationItem({ conv }: { conv: Conversation }) {
  const { t } = useTranslation()
  const { activeConversationId, setActiveConversation } = useChatStore()
  const isActive = activeConversationId === conv.id
  const [deleteOpen, setDeleteOpen] = useState(false)

  return (
    <>
      <div className={`group flex items-center gap-1 rounded-md transition-colors min-w-0 w-full ${
        isActive ? 'bg-accent/10 border border-accent/20' : 'border border-transparent hover:bg-elevated'
      }`}>
        {/* Main row — takes all available space */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setActiveConversation(conv.id)}
          onKeyDown={(e) => e.key === 'Enter' && setActiveConversation(conv.id)}
          className="flex-1 min-w-0 flex items-start gap-2 px-2 py-2 cursor-pointer"
        >
          <MessageSquare className={`size-3.5 shrink-0 mt-0.5 ${isActive ? 'text-accent' : 'text-text-tertiary'}`} />
          <div className="flex-1 min-w-0">
            <p className={`text-xs leading-tight truncate ${isActive ? 'text-accent font-medium' : 'text-text-secondary'}`}>
              {truncate(conv.title, 28)}
            </p>
            <p className="text-[10px] text-text-tertiary mt-0.5">{formatRelativeTime(conv.updatedAt)}</p>
          </div>
        </div>

        {/* Delete button — appears on row hover */}
        <button
          onClick={(e) => { e.stopPropagation(); setDeleteOpen(true) }}
          aria-label={t('sidebar.deleteConversationAria', { name: conv.title })}
          className="shrink-0 mr-1.5 h-5 w-5 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 text-text-tertiary hover:text-destructive hover:bg-destructive/10 transition-all"
        >
          <Trash2 className="size-3" />
        </button>
      </div>

      <DeleteConversationDialog
        conversation={conv}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
      />
    </>
  )
}

// ─── Upload zone ──────────────────────────────────────────────────────────────

function UploadingItem({ name, progress, status }: { name: string; progress: number; status: string }) {
  const { t } = useTranslation()
  return (
    <div className="px-2 py-2 rounded-md bg-elevated border border-border">
      <div className="flex items-center gap-2 mb-1.5">
        <FileText className="size-3 text-accent shrink-0" />
        <span className="text-[11px] text-text-primary truncate flex-1">{name}</span>
        <span className="text-[10px] text-text-tertiary">{status === 'processing' ? t('sidebar.processing') : `${Math.round(progress)}%`}</span>
      </div>
      <Progress value={progress} />
    </div>
  )
}

// ─── Main sidebar ─────────────────────────────────────────────────────────────

export function LeftSidebar() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const logout = useLogout()
  const upload = useUploadDocument()
  const [newConvOpen, setNewConvOpen] = useState(false)
  const [showAllConvs, setShowAllConvs] = useState(false)

  const navigate = useNavigate()
  const { documents, uploadingFiles } = useDocumentsStore()
  const { conversations, setActiveConversation } = useChatStore()

  const onDrop = useCallback(
    (files: File[]) => {
      files.forEach((f) => upload.mutate(f))
    },
    [upload],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/markdown': ['.md'],
    },
    noClick: true,
  })

  const initials = user?.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) ?? '?'

  return (
    <aside
      {...getRootProps()}
      className={`flex flex-col h-full w-[260px] shrink-0 bg-base border-r border-border transition-colors ${
        isDragActive ? 'bg-accent/5 border-r-accent/30' : ''
      }`}
    >
      <input {...getInputProps()} />

      {/* Header */}
      <div className="flex items-center justify-between px-3 pt-4 pb-3">
        <CitenestLogo />
        <div className="flex items-center gap-0.5">
          <LanguageSelector />
          <ThemeToggle />
        </div>
      </div>

      <Separator />

      {/* New chat button */}
      <div className="px-3 py-3">
        <Button
          className="w-full justify-start gap-2 h-8"
          size="sm"
          onClick={() => setNewConvOpen(true)}
          disabled={documents.filter((d) => d.status === 'ready').length === 0}
        >
          <Plus className="size-3.5" />
          {t('sidebar.newConversation')}
        </Button>
      </div>

      <NewConversationDialog
        open={newConvOpen}
        onOpenChange={setNewConvOpen}
        documents={documents}
      />

      {/* Upload button */}
      <div className="px-3 pb-3">
        <label className="block">
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
          <div className={`flex items-center gap-2 rounded-md border border-dashed px-3 py-2 cursor-pointer transition-colors ${
            isDragActive
              ? 'border-accent bg-accent/10 text-accent'
              : 'border-border text-text-tertiary hover:border-accent/50 hover:text-text-secondary hover:bg-elevated'
          }`}>
            <Upload className="size-3.5 shrink-0" />
            <span className="text-xs">{isDragActive ? t('sidebar.dropToUpload') : t('sidebar.uploadDocument')}</span>
          </div>
        </label>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        <div className="px-3 pb-3 space-y-4 w-full">

          {/* Uploading files */}
          {uploadingFiles.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider px-1">{t('sidebar.uploading')}</p>
              {uploadingFiles.map((f) => (
                <UploadingItem key={f.id} name={f.name} progress={f.progress} status={f.status} />
              ))}
            </div>
          )}

          {/* Documents list */}
          <div>
            <div className="flex items-center justify-between px-1 mb-1.5">
              <p className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider">{t('sidebar.documents')}</p>
              {documents.length > 0 && (
                <span className="text-[10px] text-text-tertiary">{documents.length}</span>
              )}
            </div>
            {documents.length === 0 ? (
              <div className="px-2 py-3 text-xs text-text-tertiary text-center">
                {t('sidebar.noDocuments')}
              </div>
            ) : (
              <div className="space-y-0.5">
                {documents.slice(0, 8).map((doc) => (
                  <DocumentItem key={doc.id} doc={doc} />
                ))}
                {documents.length > 8 && (
                  <Link
                    to="/documents"
                    className="block text-[11px] text-text-tertiary hover:text-accent px-2 py-1 transition-colors"
                  >
                    {t('sidebar.moreDocuments', { count: documents.length - 8 })}
                  </Link>
                )}
              </div>
            )}
          </div>

          {/* Chat history */}
          {conversations.length > 0 && (
            <div>
              <div className="flex items-center justify-between px-1 mb-1.5">
                <p className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider">{t('sidebar.conversations')}</p>
                <span className="text-[10px] text-text-tertiary">{conversations.length}</span>
              </div>
              <div className="space-y-0.5">
                {(showAllConvs ? conversations : conversations.slice(0, 8)).map((conv) => (
                  <ConversationItem key={conv.id} conv={conv} />
                ))}
              </div>
              {conversations.length > 8 && (
                <button
                  onClick={() => setShowAllConvs((v) => !v)}
                  className="flex items-center gap-1 text-[11px] text-text-tertiary hover:text-accent px-2 py-1 mt-0.5 transition-colors w-full"
                >
                  <ChevronDown className={`size-3 transition-transform ${showAllConvs ? 'rotate-180' : ''}`} />
                  {showAllConvs ? t('sidebar.showLess') : t('sidebar.showMore', { count: conversations.length - 8 })}
                </button>
              )}
            </div>
          )}

        </div>
      </div>

      {/* Navigation links */}
      <Separator />
      <nav className="px-3 py-2 space-y-0.5">
        {/* Dashboard resets to empty state */}
        <button
          onClick={() => {
            setActiveConversation(null)
            navigate('/dashboard')
          }}
          className="w-full flex items-center gap-2.5 rounded-md px-2 py-1.5 text-xs text-text-secondary hover:bg-elevated hover:text-text-primary transition-colors"
        >
          <LayoutDashboard className="size-3.5 shrink-0" />
          {t('nav.dashboard')}
        </button>
        {[
          { icon: FileText, label: t('nav.documents'), to: '/documents' },
          { icon: CreditCard, label: t('nav.billing'), to: '/billing' },
          { icon: Settings, label: t('nav.settings'), to: '/settings' },
        ].map(({ icon: Icon, label, to }) => (
          <Link
            key={to}
            to={to}
            className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-xs text-text-secondary hover:bg-elevated hover:text-text-primary transition-colors"
          >
            <Icon className="size-3.5 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      {/* User menu */}
      <Separator />
      <div className="px-3 py-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="w-full flex items-center gap-2.5 rounded-md px-2 py-2 hover:bg-elevated transition-colors group">
              <Avatar className="h-7 w-7">
                <AvatarImage src={user?.avatarUrl} alt={user?.name} />
                <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-medium text-text-primary truncate">{user?.name ?? t('common.user')}</p>
                <p className="text-[10px] text-text-tertiary truncate">{user?.email}</p>
              </div>
              <MoreHorizontal className="size-3.5 text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-52">
            <DropdownMenuLabel className="normal-case text-xs font-normal text-text-secondary pb-2">
              <p className="font-medium text-text-primary">{user?.name}</p>
              <p className="text-[11px]">{user?.email}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/settings"><User />{t('nav.profile')}</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/billing"><CreditCard />{t('nav.billing')}</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              destructive
              onClick={() => logout.mutate()}
            >
              <LogOut />{t('nav.signOut')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  )
}
