import { LeftSidebar } from '../components/LeftSidebar'
import { ChatPanel } from '../components/ChatPanel'
import { RightPanel } from '../components/RightPanel'
import { useDocuments } from '@/features/documents/hooks/use-documents'
import { useConversations } from '@/features/chat/hooks/use-chat'

export function DashboardPage() {
  // Pre-load data
  useDocuments()
  useConversations()

  return (
    <div className="flex h-screen w-full overflow-hidden bg-base">
      {/* LEFT — 260px fixed */}
      <LeftSidebar />

      {/* CENTER — flex grow */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <ChatPanel />
      </main>

      {/* RIGHT — 300px fixed, hidden on smaller screens */}
      <div className="hidden lg:block">
        <RightPanel />
      </div>
    </div>
  )
}
