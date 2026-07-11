import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Document, Page, pdfjs, type TextItem } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import { ChevronLeft, ChevronRight, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

function normalize(s: string): string {
  return s.toLowerCase().replace(/\s+/g, ' ').trim()
}

// Minimum normalized length for a text-layer item to be eligible for highlighting —
// short fragments (single letters, stray punctuation) match almost anywhere in the
// snippet and would light up the whole page.
const MIN_MATCH_LENGTH = 4

interface PdfPageHighlightProps {
  blobUrl: string
  pageNumber: number
  snippet: string
  onPageChange: (page: number) => void
  onExit: () => void
}

export function PdfPageHighlight({ blobUrl, pageNumber, snippet, onPageChange, onExit }: PdfPageHighlightProps) {
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(0)
  const [numPages, setNumPages] = useState<number | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width
      if (width) setContainerWidth(Math.min(width - 32, 900))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const normalizedSnippet = useMemo(() => normalize(snippet), [snippet])

  const textRenderer = useCallback(
    ({ str }: TextItem & { pageIndex: number; pageNumber: number; itemIndex: number }) => {
      const normalizedItem = normalize(str)
      if (normalizedItem.length >= MIN_MATCH_LENGTH && normalizedSnippet.includes(normalizedItem)) {
        return `<mark class="pdf-highlight">${str}</mark>`
      }
      return str
    },
    [normalizedSnippet],
  )

  const handleTextLayerRendered = useCallback(() => {
    requestAnimationFrame(() => {
      containerRef.current
        ?.querySelector('mark.pdf-highlight')
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }, [])

  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-border bg-elevated/50">
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onPageChange(pageNumber - 1)}
            disabled={pageNumber <= 1}
          >
            <ChevronLeft className="size-4" />
          </Button>
          <span className="text-xs text-text-secondary font-mono tabular-nums">
            {numPages ? `${pageNumber} / ${numPages}` : pageNumber}
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onPageChange(pageNumber + 1)}
            disabled={numPages !== null && pageNumber >= numPages}
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={onExit}>
          {t('documents.viewFullDocument')}
        </Button>
      </div>

      {/* Page */}
      <div
        ref={containerRef}
        className="flex justify-center overflow-y-auto bg-base py-6"
        style={{ height: 'calc(100vh - 340px)', minHeight: 400 }}
      >
        {error ? (
          <div className="flex flex-col items-center justify-center text-center px-8">
            <AlertCircle className="size-8 text-text-tertiary mb-3" />
            <p className="text-sm text-text-secondary">{t('documents.previewFailed')}</p>
          </div>
        ) : (
          <Document
            file={blobUrl}
            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
            onLoadError={() => setError(true)}
            loading={<Loader2 className="size-6 text-accent animate-spin mt-16" />}
          >
            {containerWidth > 0 && (
              <Page
                key={pageNumber}
                pageNumber={pageNumber}
                width={containerWidth}
                customTextRenderer={textRenderer}
                onRenderTextLayerSuccess={handleTextLayerRendered}
                loading={<Loader2 className="size-6 text-accent animate-spin mt-16" />}
                className="shadow-lg"
              />
            )}
          </Document>
        )}
      </div>

      <div className="px-4 py-2 border-t border-border-subtle">
        <p className="text-[11px] text-text-tertiary">{t('documents.highlightHint')}</p>
      </div>
    </div>
  )
}
