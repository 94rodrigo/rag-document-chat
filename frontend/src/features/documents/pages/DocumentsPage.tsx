import { useState, useCallback, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft, Upload, Search, FileText, Loader2, LayoutGrid, List
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Progress } from '@/shared/components/ui/progress'
import { Skeleton } from '@/shared/components/ui/skeleton'
import { DocumentCard } from '../components/DocumentCard'
import { SourceCard } from '../components/SourceCard'
import { useDocuments, useUploadDocument, useDocumentSearch } from '../hooks/use-documents'
import { useDocumentsStore } from '../stores/documents-store'

const SEARCH_DEBOUNCE_MS = 350

export function DocumentsPage() {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  const { isLoading } = useDocuments()
  const upload = useUploadDocument()
  const { documents, uploadingFiles } = useDocumentsStore()

  // Debounced so every keystroke doesn't trigger an embedding + rerank round trip.
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [search])

  const isSearchQuery = debouncedSearch.length >= 2
  const { data: searchResults, isLoading: searchLoading } = useDocumentSearch(debouncedSearch)

  const onDrop = useCallback(
    (files: File[]) => files.forEach((f) => upload.mutate(f)),
    [upload],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: true,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/markdown': ['.md'],
    },
  })

  return (
    <div
      {...getRootProps()}
      className={`min-h-screen bg-base transition-colors ${
        isDragActive ? 'bg-accent/3' : ''
      }`}
    >
      <input {...getInputProps()} />

      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between px-8 py-4 border-b border-border bg-base/80 glass">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" asChild>
            <Link to="/dashboard"><ArrowLeft className="size-4" /></Link>
          </Button>
          <div>
            <h1 className="font-display text-lg text-text-primary leading-tight">{t('documents.title')}</h1>
            <p className="text-xs text-text-tertiary">{t('documents.count', { count: documents.length })}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
          >
            {viewMode === 'grid' ? <List className="size-4" /> : <LayoutGrid className="size-4" />}
          </Button>
          <label>
            <input
              type="file"
              className="sr-only"
              multiple
              accept=".pdf,.txt,.docx,.md"
              onChange={(e) => {
                Array.from(e.target.files ?? []).forEach((f) => upload.mutate(f))
                e.target.value = ''
              }}
            />
            <Button size="sm" asChild>
              <span className="cursor-pointer">
                <Upload className="size-3.5" />
                {t('documents.upload')}
              </span>
            </Button>
          </label>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-8 py-6">
        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-text-tertiary" />
          <Input
            placeholder={t('documents.searchPlaceholder')}
            className="ps-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Drop zone hint */}
        {isDragActive && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-6 rounded-xl border-2 border-dashed border-accent/40 bg-accent/5 py-10 text-center"
          >
            <Upload className="size-8 text-accent mx-auto mb-2" />
            <p className="text-sm font-medium text-accent">{t('documents.dropToUpload')}</p>
          </motion.div>
        )}

        {/* Uploading files */}
        {uploadingFiles.length > 0 && (
          <div className="mb-6 space-y-2">
            <p className="text-xs text-text-tertiary uppercase tracking-wider mb-2">{t('documents.uploading')}</p>
            {uploadingFiles.map((f) => (
              <div key={f.id} className="rounded-lg border border-border bg-surface p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Loader2 className="size-3.5 text-accent animate-spin" />
                  <span className="text-xs text-text-primary flex-1 truncate">{f.name}</span>
                  <span className="text-[10px] text-text-tertiary">
                    {f.status === 'processing' ? t('documents.processing') : `${Math.round(f.progress)}%`}
                  </span>
                </div>
                <Progress value={f.progress} />
              </div>
            ))}
          </div>
        )}

        {/* Semantic search results — passages, not documents */}
        {isSearchQuery ? (
          searchLoading ? (
            <div className="space-y-2">
              <p className="text-xs text-text-tertiary uppercase tracking-wider mb-2">{t('documents.searching')}</p>
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-28 w-full" />
              ))}
            </div>
          ) : !searchResults?.length ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="h-14 w-14 rounded-2xl bg-elevated border border-border flex items-center justify-center mb-4">
                <Search className="size-6 text-text-tertiary" />
              </div>
              <h3 className="font-display text-xl text-text-primary mb-2">{t('documents.noMatches')}</h3>
              <p className="text-sm text-text-secondary max-w-xs mb-5">
                {t('documents.noMatchesFor', { search: debouncedSearch })}
              </p>
              <Button variant="outline" size="sm" onClick={() => setSearch('')}>
                {t('documents.clearSearch')}
              </Button>
            </div>
          ) : (
            <div className="space-y-2 max-w-2xl">
              <p className="text-xs text-text-tertiary uppercase tracking-wider mb-2">
                {t('documents.searchResultsCount', { count: searchResults.length })}
              </p>
              {searchResults.map((chunk, i) => (
                <SourceCard key={chunk.id} chunk={chunk} index={i} />
              ))}
            </div>
          )
        ) : isLoading ? (
          <div className={`grid gap-3 ${viewMode === 'grid' ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="h-14 w-14 rounded-2xl bg-elevated border border-border flex items-center justify-center mb-4">
              <FileText className="size-6 text-text-tertiary" />
            </div>
            <h3 className="font-display text-xl text-text-primary mb-2">
              {t('documents.noDocuments')}
            </h3>
            <p className="text-sm text-text-secondary max-w-xs mb-5">
              {t('documents.noDocumentsBody')}
            </p>
            <label className="cursor-pointer">
              <input
                type="file"
                className="sr-only"
                multiple
                accept=".pdf,.txt,.docx,.md"
                onChange={(e) => {
                  Array.from(e.target.files ?? []).forEach((f) => upload.mutate(f))
                  e.target.value = ''
                }}
              />
              <Button size="sm" asChild>
                <span>
                  <Upload className="size-3.5" />
                  {t('documents.uploadFirst')}
                </span>
              </Button>
            </label>
          </div>
        ) : (
          <div className={`grid gap-3 ${viewMode === 'grid' ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
            {documents.map((doc, i) => (
              <DocumentCard key={doc.id} doc={doc} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
