import { formatConversationTime } from '../data/mockData'
import UploadPanel from './UploadPanel'

function AccessSidebar({
  currentUser,
  documents,
  conversations,
  activeConversationId,
  onConversationSelect,
  onDeleteConversation,
  onNewChat,
  uploadVisibilityScope,
  onUploadVisibilityChange,
  onFileUpload,
  onToggle,
}) {
  return (
    <aside className="flex min-h-[70vh] flex-col gap-4 rounded-3xl border border-white/10 bg-[#171717] p-4 xl:h-full xl:min-h-0">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium text-white">History</h2>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-full border border-white/10 bg-[#212121] px-3 py-1 text-xs text-zinc-300 transition hover:bg-[#2a2a2a]"
        >
          Close
        </button>
      </div>

      <button
        type="button"
        onClick={onNewChat}
        className="rounded-2xl border border-white/10 bg-[#212121] px-4 py-3 text-left text-sm text-white transition hover:bg-[#2a2a2a]"
      >
        + New chat
      </button>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            className={`block w-full rounded-2xl border px-3 py-3 text-left transition ${
              conversation.id === activeConversationId
                ? 'border-white/20 bg-[#2a2a2a]'
                : 'border-white/10 bg-[#212121] hover:bg-[#2a2a2a]'
            }`}
          >
            <div className="flex items-start gap-3">
              <button
                type="button"
                onClick={() => onConversationSelect(conversation.id)}
                className="min-w-0 flex-1 text-left"
              >
                <p className="truncate text-sm text-white">{conversation.title}</p>
                <p className="mt-1 text-xs text-zinc-500">{formatConversationTime(conversation.updatedAt)}</p>
              </button>

              <button
                type="button"
                onClick={() => onDeleteConversation(conversation.id)}
                className="rounded-full border border-white/10 bg-[#171717] px-2 py-1 text-[11px] text-zinc-400 transition hover:bg-[#303030] hover:text-white"
                aria-label={`Delete chat ${conversation.title}`}
                title="Delete chat"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      <UploadPanel
        currentUser={currentUser}
        uploadVisibilityScope={uploadVisibilityScope}
        onUploadVisibilityChange={onUploadVisibilityChange}
        onFileUpload={onFileUpload}
        totalCount={documents.length}
      />
    </aside>
  )
}

export default AccessSidebar
