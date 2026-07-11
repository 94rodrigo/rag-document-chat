import { useParams, Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, MessageSquare, Download, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Skeleton } from '@/shared/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs'
import { ScrollArea } from '@/shared/components/ui/scroll-area'
import { documentsApi } from '@/shared/lib/api-client'
import { useCreateConversation } from '@/features/chat/hooks/use-chat'
import { getMimeTypeLabel, formatBytes, formatRelativeTime } from '@/shared/lib/utils'
import { useDocumentsStore } from '../stores/documents-store'
import { PdfPageHighlight } from '../components/PdfPageHighlight'

function usePdfBlobUrl(docId: string | undefined, mimeType: string | undefined) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!docId || mimeType !== 'application/pdf') return

    let revoked = false
    setLoading(true)
    setError(false)

    const token = localStorage.getItem('access_token')
    fetch(`/api/v1/documents/${docId}/file`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`)
        return r.blob()
      })
      .then((blob) => {
        if (revoked) return
        const url = URL.createObjectURL(blob)
        setBlobUrl(url)
        setLoading(false)
      })
      .catch(() => {
        if (!revoked) { setError(true); setLoading(false) }
      })

    return () => {
      revoked = true
      setBlobUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null })
    }
  }, [docId, mimeType])

  return { blobUrl, loading, error }
}

export function DocumentViewerPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialPage = searchParams.get('page')
  const createConversation = useCreateConversation()
  const { documents } = useDocumentsStore()

  const doc = documents.find((d) => d.id === id)

  const { blobUrl, loading: pdfLoading, error: pdfError } = usePdfBlobUrl(id, doc?.mimeType)

  // A citation click carries the exact chunk text via router state so the target
  // page can be rendered with that passage highlighted, not just scrolled to.
  // Captured into local state (rather than read directly from location.state)
  // because prev/next navigation inside highlight mode goes through
  // setSearchParams, which clears router state on every call — the effect below
  // only ever *sets* a new snippet when one genuinely arrives, so it survives.
  const [snippet, setSnippet] = useState<string | undefined>(
    () => (location.state as { snippet?: string } | null)?.snippet,
  )
  const [exitedHighlight, setExitedHighlight] = useState(false)

  useEffect(() => {
    const incoming = (location.state as { snippet?: string } | null)?.snippet
    if (incoming) {
      setSnippet(incoming)
      setExitedHighlight(false)
    }
  }, [location.state])

  const showHighlight = !!snippet && !!initialPage && !exitedHighlight
  const highlightPage = initialPage ? parseInt(initialPage, 10) : 1

  const handleHighlightPageChange = (page: number) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('page', String(page))
      return next
    })
  }

  const { data: chunksData, isLoading: chunksLoading } = useQuery({
    queryKey: ['document-chunks', id],
    queryFn: () => documentsApi.getChunks(id!),
    enabled: !!id,
  })

  const handleChat = () => {
    if (id) {
      createConversation.mutate([id])
      navigate('/dashboard')
    }
  }

  const handleDownload = () => {
    const token = localStorage.getItem('access_token')
    fetch(`/api/v1/documents/${id}/file?download=1`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = doc?.name ?? 'document'
        a.click()
        URL.revokeObjectURL(url)
      })
  }

  if (!doc) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-center">
        <AlertCircle className="size-10 text-text-tertiary mb-4" />
        <h2 className="font-display text-2xl text-text-primary mb-2">{t('documents.notFound')}</h2>
        <Button asChild variant="outline">
          <Link to="/documents">{t('documents.backToDocuments')}</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-base flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between px-8 py-4 border-b border-border bg-base/80 glass">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" asChild>
            <Link to="/documents"><ArrowLeft className="size-4" /></Link>
          </Button>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
              <FileText className="size-4 text-accent" />
            </div>
            <div>
              <h1 className="text-sm font-medium text-text-primary leading-tight">{doc.name}</h1>
              <div className="flex items-center gap-2 mt-0.5">
                <Badge variant="secondary" className="text-[9px]">{getMimeTypeLabel(doc.mimeType)}</Badge>
                <span className="text-[10px] text-text-tertiary">{formatBytes(doc.sizeBytes)}</span>
                {doc.pageCount && <span className="text-[10px] text-text-tertiary">{t('documents.pages', { count: doc.pageCount })}</span>}
                <span className="text-[10px] text-text-tertiary">{formatRelativeTime(doc.createdAt)}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleChat}>
            <MessageSquare className="size-3.5" />
            {t('documents.askQuestions')}
          </Button>
          <Button variant="ghost" size="icon-sm" onClick={handleDownload} title={t('common.download')}>
            <Download className="size-4" />
          </Button>
        </div>
      </header>

      <div className="flex-1 max-w-5xl mx-auto w-full px-8 py-6">
        <Tabs defaultValue="preview">
          <TabsList className="mb-4">
            <TabsTrigger value="preview">{t('documents.preview')}</TabsTrigger>
            <TabsTrigger value="chunks">{t('documents.indexedChunks')}</TabsTrigger>
          </TabsList>

          <TabsContent value="preview">
            {doc.mimeType === 'application/pdf' && showHighlight && blobUrl ? (
              <PdfPageHighlight
                blobUrl={blobUrl}
                pageNumber={highlightPage}
                snippet={snippet!}
                onPageChange={handleHighlightPageChange}
                onExit={() => setExitedHighlight(true)}
              />
            ) : (
              <div className="rounded-xl border border-border bg-surface overflow-hidden">
                {doc.mimeType === 'application/pdf' ? (
                  pdfLoading ? (
                    <div className="flex items-center justify-center h-[calc(100vh-280px)] min-h-[400px]">
                      <Loader2 className="size-6 text-accent animate-spin" />
                    </div>
                  ) : pdfError ? (
                    <div className="flex flex-col items-center justify-center h-[calc(100vh-280px)] min-h-[400px] text-center">
                      <AlertCircle className="size-8 text-text-tertiary mb-3" />
                      <p className="text-sm text-text-secondary">{t('documents.previewFailed')}</p>
                      <Button variant="outline" size="sm" className="mt-3" onClick={handleDownload}>
                        <Download className="size-3.5" /> {t('documents.downloadInstead')}
                      </Button>
                    </div>
                  ) : (
                    <iframe
                      key={`${blobUrl}#${initialPage}`}
                      src={initialPage ? `${blobUrl}#page=${initialPage}` : blobUrl!}
                      className="w-full h-[calc(100vh-280px)] min-h-[400px]"
                      title={doc.name}
                    />
                  )
                ) : (
                  <div className="p-8 text-sm text-text-secondary font-mono leading-relaxed whitespace-pre-wrap">
                    {t('documents.previewUnavailable')}
                    <br />
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-4"
                      onClick={handleChat}
                    >
                      <MessageSquare className="size-3.5" />
                      {t('documents.chatInstead')}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="chunks">
            <ScrollArea className="h-[calc(100vh-280px)]">
              {chunksLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-20 w-full" />
                  ))}
                </div>
              ) : !chunksData?.length ? (
                <div className="text-center py-16 text-text-secondary">
                  <p className="text-sm">{t('documents.noChunks')}</p>
                  {doc.status === 'processing' && (
                    <p className="text-xs text-text-tertiary mt-1">{t('documents.stillIndexing')}</p>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {chunksData.map((chunk, i) => (
                    <div
                      key={chunk.id}
                      className="rounded-lg border border-border bg-surface p-4"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-mono text-text-tertiary">{t('documents.chunk', { index: i + 1 })}</span>
                        {chunk.pageNumber && (
                          <Badge variant="secondary" className="text-[9px]">p.{chunk.pageNumber}</Badge>
                        )}
                      </div>
                      <p className="text-xs text-text-secondary font-mono leading-relaxed">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
