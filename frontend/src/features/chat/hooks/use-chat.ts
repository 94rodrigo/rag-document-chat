import { useCallback, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import i18n from '@/shared/i18n'
import { chatApi } from '@/shared/lib/api-client'
import { generateId } from '@/shared/lib/utils'
import { useChatStore } from '../stores/chat-store'
import type { ChatMessage, Citation, DocumentChunk } from '@/shared/types'

export function useConversations() {
  const setConversations = useChatStore((s) => s.setConversations)
  return useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      const res = await chatApi.listConversations()
      setConversations(res)
      return res
    },
  })
}

function citationsToChunks(citations: Citation[]): DocumentChunk[] {
  return citations.map((c) => ({
    id: c.chunkId,
    documentId: c.documentId,
    documentName: c.documentName,
    content: c.content,
    pageNumber: c.pageNumber,
    score: c.score,
    metadata: {},
  }))
}

export function useMessages(conversationId: string | null) {
  const setMessages = useChatStore((s) => s.setMessages)
  const setSourceChunks = useChatStore((s) => s.setSourceChunks)
  const setActiveCitations = useChatStore((s) => s.setActiveCitations)

  const query = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: async () => {
      const messages = await chatApi.getMessages(conversationId!)
      setMessages(conversationId!, messages)
      return messages
    },
    enabled: !!conversationId,
  })

  // Sync the Sources panel from the last assistant message's citations whenever
  // this conversation's data is the active one — including cache hits, where
  // queryFn above does not re-run.
  useEffect(() => {
    if (!conversationId || !query.data) return

    const lastWithCitations = [...query.data]
      .reverse()
      .find((m) => m.role === 'assistant' && m.citations && m.citations.length > 0)
    const citations = lastWithCitations?.citations ?? []

    setActiveCitations(citations)
    setSourceChunks(citationsToChunks(citations))
  }, [conversationId, query.data, setActiveCitations, setSourceChunks])

  return query
}

export function useCreateConversation() {
  const qc = useQueryClient()
  const setActiveConversation = useChatStore((s) => s.setActiveConversation)

  return useMutation({
    mutationFn: (documentIds: string[]) =>
      chatApi.createConversation(documentIds),
    onSuccess: (conv) => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
      setActiveConversation(conv.id)
    },
    onError: () => toast.error(i18n.t('chat.toasts.couldNotStart')),
  })
}

export function useDeleteConversation() {
  const qc = useQueryClient()
  const { removeConversation, activeConversationId, setActiveConversation } = useChatStore()

  return useMutation({
    mutationFn: (id: string) => chatApi.deleteConversation(id),
    onSuccess: (_data, id) => {
      removeConversation(id)
      if (activeConversationId === id) setActiveConversation(null)
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
    onError: () => toast.error(i18n.t('chat.toasts.couldNotDelete')),
  })
}

export function useSendMessage() {
  const abortRef = useRef<AbortController | null>(null)
  const qc = useQueryClient()
  const {
    activeConversationId,
    appendMessage,
    updateStreamingMessage,
    finalizeStreamingMessage,
    setIsStreaming,
    setActiveCitations,
    setSourceChunks,
  } = useChatStore()

  const sendMessage = useCallback(
    async (content: string) => {
      if (!activeConversationId || !content.trim()) return

      // Optimistically add user message
      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
      }
      appendMessage(activeConversationId, userMsg)
      setIsStreaming(true)

      abortRef.current = new AbortController()
      let accumulated = ''

      try {
        const { message, citations } = await chatApi.sendMessage(
          activeConversationId,
          content,
          (chunk) => {
            if (chunk.type === 'text' && chunk.content) {
              accumulated += chunk.content
              updateStreamingMessage(activeConversationId, accumulated)
            }
          },
          abortRef.current.signal,
        )

        const finalMsg = message ?? {
          id: generateId(),
          role: 'assistant' as const,
          content: accumulated,
          citations,
          createdAt: new Date().toISOString(),
        }

        finalizeStreamingMessage(activeConversationId, finalMsg)
        setActiveCitations(citations)
        // Refresh conversation list so auto-generated title appears in sidebar
        qc.invalidateQueries({ queryKey: ['conversations'] })

        // Map citations to source chunks for the right panel
        const chunks: DocumentChunk[] = citations.map((c) => ({
          id: c.chunkId,
          documentId: c.documentId,
          documentName: c.documentName,
          content: c.content,
          pageNumber: c.pageNumber,
          score: c.score,
          metadata: {},
        }))
        setSourceChunks(chunks)
      } catch (err: unknown) {
        if ((err as Error).name === 'AbortError') return
        setIsStreaming(false)
        toast.error(i18n.t('chat.toasts.failedResponse'))
      }
    },
    [
      activeConversationId,
      appendMessage,
      updateStreamingMessage,
      finalizeStreamingMessage,
      setIsStreaming,
      setActiveCitations,
      setSourceChunks,
      qc,
    ],
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [setIsStreaming])

  return { sendMessage, abort }
}
