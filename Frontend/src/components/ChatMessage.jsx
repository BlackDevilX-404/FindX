import CitationChip from './CitationChip'

function ChatMessage({
  message,
  onSourceSelect,
  selectedSource,
  onSuggestedQuery,
  suggestedQueries = [],
}) {
  if (message.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-2xl rounded-[28px] bg-[#303030] px-4 py-3 text-sm leading-7 text-white">
          {message.text}
        </div>
      </div>
    )
  }

  return (
    <div className="w-full">
      <div className="max-w-3xl text-sm leading-7 text-zinc-100">
        {message.isStreaming && (message.agentStatus || message.agentDetail) ? (
          <div className="mb-3 rounded-2xl border border-white/10 bg-[#242424] px-4 py-3 text-xs text-zinc-300">
            <p className="font-medium text-zinc-100">
              {message.agentStatus ? `${message.agentStatus}...` : 'Working...'}
            </p>
            {message.agentDetail ? (
              <p className="mt-1 text-zinc-400">{message.agentDetail}</p>
            ) : null}
          </div>
        ) : null}

        <p className="whitespace-pre-wrap">
          {message.text}
          {message.isStreaming ? (
            <span className="ml-1 inline-block h-4 w-[2px] animate-pulse bg-zinc-300 align-middle" />
          ) : null}
        </p>

        {message.suggested && suggestedQueries.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {suggestedQueries.map((query) => (
              <button
                key={query}
                type="button"
                onClick={() => onSuggestedQuery(query)}
                className="rounded-full border border-white/10 bg-[#2a2a2a] px-3 py-2 text-xs text-zinc-200 transition hover:bg-[#343434]"
              >
                {query}
              </button>
            ))}
          </div>
        ) : null}

        {message.sources?.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.sources.map((source) => (
              <CitationChip
                key={source.id}
                source={source}
                isActive={selectedSource?.id === source.id}
                onClick={() => onSourceSelect(source)}
              />
            ))}
          </div>
        ) : null}

        {message.explanation ? (
          <p className="mt-3 text-sm text-zinc-400">{message.explanation}</p>
        ) : null}
      </div>
    </div>
  )
}

export default ChatMessage
