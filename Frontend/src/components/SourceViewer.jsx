function SourceViewer({ selectedSource, onToggle }) {
  return (
    <aside className="flex min-h-[70vh] flex-col rounded-3xl border border-[var(--border-soft)] bg-[var(--surface-1)] xl:h-full xl:min-h-0">
      <div className="flex items-center justify-between border-b border-[var(--border-soft)] px-4 py-4">
        <div>
          <h2 className="text-sm font-medium text-[var(--text-main)]">Evidence</h2>
          <p className="mt-1 text-xs text-[var(--text-muted)]">Trace each answer back to its source</p>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-1 text-xs text-[var(--text-main)] hover:bg-[var(--surface-3)]"
        >
          Close
        </button>
      </div>

      {selectedSource ? (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4">
          <div className="rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-2)] p-4">
            <p className="text-sm font-medium text-[var(--text-main)]">{selectedSource.doc}</p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              {selectedSource.page ? `Page ${selectedSource.page}` : 'Retrieved snippet'}
              {selectedSource.confidence ? ` | ${selectedSource.confidence}` : ''}
            </p>
          </div>

          <div className="mt-4 rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-2)] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Snippet</p>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-[var(--text-main)]">
              {selectedSource.text || selectedSource.summary || 'No evidence snippet available.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--text-muted)]">
          Select a citation to inspect the supporting context.
        </div>
      )}
    </aside>
  )
}

export default SourceViewer
