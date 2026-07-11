import { create } from 'zustand'
import type { ChatMessage, Citation, Conversation, DocumentChunk } from '@/shared/types'

interface ChatState {
  conversations: Conversation[]
  activeConversationId: string | null
  messages: Record<string, ChatMessage[]>
  sourcePanelChunks: DocumentChunk[]
  activeCitations: Citation[]
  isStreaming: boolean
  streamingContent: string

  setConversations: (convs: Conversation[]) => void
  removeConversation: (id: string) => void
  setActiveConversation: (id: string | null) => void
  setMessages: (conversationId: string, messages: ChatMessage[]) => void
  appendMessage: (conversationId: string, message: ChatMessage) => void
  updateStreamingMessage: (conversationId: string, content: string) => void
  finalizeStreamingMessage: (conversationId: string, message: ChatMessage) => void
  setSourceChunks: (chunks: DocumentChunk[]) => void
  setActiveCitations: (citations: Citation[]) => void
  setIsStreaming: (v: boolean) => void
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  activeConversationId: null,
  messages: {},
  sourcePanelChunks: [],
  activeCitations: [],
  isStreaming: false,
  streamingContent: '',

  setConversations: (conversations) => set({ conversations }),

  removeConversation: (id) =>
    set((s) => ({ conversations: s.conversations.filter((c) => c.id !== id) })),

  setActiveConversation: (id) =>
    set({ activeConversationId: id, activeCitations: [], sourcePanelChunks: [] }),

  setMessages: (conversationId, messages) =>
    set((s) => ({ messages: { ...s.messages, [conversationId]: messages } })),

  appendMessage: (conversationId, message) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [conversationId]: [...(s.messages[conversationId] ?? []), message],
      },
    })),

  updateStreamingMessage: (_conversationId, content) =>
    set({ streamingContent: content }),

  finalizeStreamingMessage: (conversationId, message) =>
    set((s) => ({
      isStreaming: false,
      streamingContent: '',
      messages: {
        ...s.messages,
        [conversationId]: [...(s.messages[conversationId] ?? []), message],
      },
    })),

  setSourceChunks: (sourcePanelChunks) => set({ sourcePanelChunks }),
  setActiveCitations: (activeCitations) => set({ activeCitations }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
}))
