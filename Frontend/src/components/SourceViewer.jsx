function SourceViewer({ selectedSource, onToggle }) {
  return (
    <aside className="flex min-h-[70vh] flex-col rounded-3xl border border-white/10 bg-[#171717] xl:h-full xl:min-h-0">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-4">
        <h2 className="text-sm font-medium text-white">Evidence</h2>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-full border border-white/10 bg-[#212121] px-3 py-1 text-xs text-zinc-300 transition hover:bg-[#2a2a2a]"
        >
          Close
        </button>
      </div>

      {selectedSource ? (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4">
          <div className="rounded-2xl border border-white/10 bg-[#212121] p-4">
            <p className="text-sm font-medium text-white">{selectedSource.doc}</p>
            <p className="mt-1 text-xs text-zinc-500">
              {selectedSource.page ? `Page ${selectedSource.page}` : 'Retrieved snippet'}
              {selectedSource.confidence ? ` | ${selectedSource.confidence}` : ''}
            </p>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-[#212121] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Snippet</p>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-zinc-200">
              {selectedSource.text || selectedSource.summary || 'No evidence snippet available.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-zinc-500">
          Select a citation to inspect the evidence.
        </div>
      )}
    </aside>
  )
}

export default SourceViewer
