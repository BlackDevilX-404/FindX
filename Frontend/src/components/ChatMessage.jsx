import CitationChip from './CitationChip'

function ChatMessage({
  message,
  role,
  onSourceSelect,
  selectedSource,
  onSuggestedQuery,
  suggestedQueries,
}) {
  if (message.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-2xl rounded-[24px] rounded-br-md bg-gradient-to-br from-blue-500 to-indigo-500 px-4 py-3 text-sm text-white shadow-lg shadow-blue-950/30">
          {message.text}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 text-sm font-semibold text-white shadow-md shadow-indigo-950/30">
        AI
      </div>

      <div className="max-w-3xl flex-1 rounded-[24px] rounded-bl-md border border-white/10 bg-white/[0.08] px-4 py-4 text-sm text-slate-200 shadow-lg shadow-slate-950/20">
        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">
              {message.kind === 'welcome' ? `${role} workspace` : 'Answer'}
            </p>
            <p className="mt-2 text-[15px] leading-7 text-slate-100">{message.text}</p>
          </div>

          {message.suggested ? (
            <div className="flex flex-wrap gap-2">
              {suggestedQueries.map((query) => (
                <button
                  key={query}
                  type="button"
                  onClick={() => onSuggestedQuery(query)}
                  className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-2 text-xs text-slate-200 transition hover:border-blue-300/40 hover:bg-blue-500/10"
                >
                  {query}
                </button>
              ))}
            </div>
          ) : null}

          {message.sources?.length ? (
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Sources</p>
              <div className="flex flex-wrap gap-2">
                {message.sources.map((source) => (
                  <CitationChip
                    key={source.id}
                    source={source}
                    isActive={selectedSource?.id === source.id}
                    onClick={() => onSourceSelect(source)}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {message.explanation ? (
            <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.08] p-3">
              <p className="text-xs uppercase tracking-[0.25em] text-cyan-200/80">
                Why this answer?
              </p>
              <p className="mt-2 leading-6 text-slate-200">{message.explanation}</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default ChatMessage
