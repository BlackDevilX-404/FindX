import ChatMessage from './ChatMessage'

function ChatWindow({
  messages,
  isTyping,
  role,
  onSourceSelect,
  onSuggestedQuery,
  selectedSource,
  suggestedQueries,
  chatViewportRef,
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={chatViewportRef} className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            role={role}
            onSourceSelect={onSourceSelect}
            selectedSource={selectedSource}
            onSuggestedQuery={onSuggestedQuery}
            suggestedQueries={suggestedQueries}
          />
        ))}

        {isTyping ? (
          <div className="flex items-end gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-500 text-sm font-semibold text-white">
              AI
            </div>
            <div className="rounded-[24px] rounded-bl-md border border-white/10 bg-white/[0.08] px-4 py-3 text-sm text-slate-300">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 animate-bounce rounded-full bg-blue-300 [animation-delay:-0.3s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-blue-300 [animation-delay:-0.15s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-blue-300" />
                <span className="ml-2 text-slate-400">Retrieving relevant FindX context</span>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export default ChatWindow
