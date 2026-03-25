import ChatMessage from './ChatMessage'

function ChatWindow({
  messages,
  isTyping,
  onSourceSelect,
  onSuggestedQuery,
  selectedSource,
  suggestedQueries,
  chatViewportRef,
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={chatViewportRef} className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onSourceSelect={onSourceSelect}
              selectedSource={selectedSource}
              onSuggestedQuery={onSuggestedQuery}
              suggestedQueries={suggestedQueries}
            />
          ))}

          {isTyping ? (
            <div className="max-w-3xl text-sm text-zinc-400">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.3s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.15s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-400" />
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default ChatWindow
