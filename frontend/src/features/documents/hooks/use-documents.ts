import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import i18n from '@/shared/i18n'
import { documentsApi } from '@/shared/lib/api-client'
import { generateId } from '@/shared/lib/utils'
import { useDocumentsStore } from '../stores/documents-store'

export const DOCUMENTS_KEY = ['documents']

export function useDocuments() {
  const setDocuments = useDocumentsStore((s) => s.setDocuments)

  return useQuery({
    queryKey: DOCUMENTS_KEY,
    queryFn: async () => {
      const res = await documentsApi.list()
      setDocuments(res.items)
      return res
    },
  })
}

export function useDeleteDocument() {
  const qc = useQueryClient()
  const removeDocument = useDocumentsStore((s) => s.removeDocument)

  return useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onMutate: (id) => removeDocument(id),
    onSuccess: () => toast.success(i18n.t('documents.toasts.deleted')),
    onError: (_err, _id) => {
      qc.invalidateQueries({ queryKey: DOCUMENTS_KEY })
      toast.error(i18n.t('documents.toasts.deleteFailed'))
    },
  })
}

export function useUploadDocument() {
  const qc = useQueryClient()
  const { addUploadingFile, updateUploadingFile, removeUploadingFile, addDocument } =
    useDocumentsStore()

  return useMutation({
    mutationFn: async (file: File) => {
      const tempId = generateId()

      addUploadingFile({
        id: tempId,
        name: file.name,
        progress: 0,
        status: 'uploading',
      })

      try {
        const res = await documentsApi.upload(file, (pct) => {
          updateUploadingFile(tempId, { progress: pct })
        })

        updateUploadingFile(tempId, { status: 'processing', progress: 100 })

        addDocument(res.document)

        // slight delay so user sees "processing" state
        await new Promise((r) => setTimeout(r, 1500))
        removeUploadingFile(tempId)
        qc.invalidateQueries({ queryKey: DOCUMENTS_KEY })

        return res.document
      } catch (err) {
        updateUploadingFile(tempId, { status: 'error', error: i18n.t('documents.toasts.uploadFailed') })
        throw err
      }
    },
    onError: (err: { message?: string }) => {
      toast.error(err.message ?? i18n.t('documents.toasts.uploadFailed'))
    },
  })
}
