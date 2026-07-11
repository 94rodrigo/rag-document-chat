import { create } from 'zustand'
import type { Document } from '@/shared/types'

interface UploadingFile {
  id: string
  name: string
  progress: number
  status: 'uploading' | 'processing' | 'done' | 'error'
  error?: string
}

interface DocumentsState {
  documents: Document[]
  selectedDocumentIds: Set<string>
  uploadingFiles: UploadingFile[]
  activeDocumentId: string | null

  setDocuments: (docs: Document[]) => void
  addDocument: (doc: Document) => void
  updateDocument: (id: string, patch: Partial<Document>) => void
  removeDocument: (id: string) => void
  toggleSelectDocument: (id: string) => void
  clearSelection: () => void
  selectAllDocuments: () => void
  setActiveDocument: (id: string | null) => void
  addUploadingFile: (file: UploadingFile) => void
  updateUploadingFile: (id: string, patch: Partial<UploadingFile>) => void
  removeUploadingFile: (id: string) => void
}

export const useDocumentsStore = create<DocumentsState>((set) => ({
  documents: [],
  selectedDocumentIds: new Set(),
  uploadingFiles: [],
  activeDocumentId: null,

  setDocuments: (documents) => set({ documents }),

  addDocument: (doc) =>
    set((s) => ({ documents: [doc, ...s.documents] })),

  updateDocument: (id, patch) =>
    set((s) => ({
      documents: s.documents.map((d) => (d.id === id ? { ...d, ...patch } : d)),
    })),

  removeDocument: (id) =>
    set((s) => ({
      documents: s.documents.filter((d) => d.id !== id),
      selectedDocumentIds: new Set([...s.selectedDocumentIds].filter((x) => x !== id)),
    })),

  toggleSelectDocument: (id) =>
    set((s) => {
      const next = new Set(s.selectedDocumentIds)
      next.has(id) ? next.delete(id) : next.add(id)
      return { selectedDocumentIds: next }
    }),

  clearSelection: () => set({ selectedDocumentIds: new Set() }),

  selectAllDocuments: () =>
    set((s) => ({ selectedDocumentIds: new Set(s.documents.map((d) => d.id)) })),

  setActiveDocument: (activeDocumentId) => set({ activeDocumentId }),

  addUploadingFile: (file) =>
    set((s) => ({ uploadingFiles: [...s.uploadingFiles, file] })),

  updateUploadingFile: (id, patch) =>
    set((s) => ({
      uploadingFiles: s.uploadingFiles.map((f) => (f.id === id ? { ...f, ...patch } : f)),
    })),

  removeUploadingFile: (id) =>
    set((s) => ({ uploadingFiles: s.uploadingFiles.filter((f) => f.id !== id) })),
}))
