import { DOCUMENT_LIBRARY, ROLE_STYLES } from '../data/mockData'

function SourceViewer({ selectedSource, role, documents }) {
  const activeDocument = selectedSource
    ? DOCUMENT_LIBRARY[selectedSource.doc] ?? {
        section: 'Manual file preview',
        content: [
          selectedSource.summary ?? 'This file was opened from the file search panel.',
          'A backend document renderer is not connected yet, so this preview shows the selected file context instead of the raw file contents.',
        ],
      }
    : null
  const isManualOpen = selectedSource?.mode === 'document'

  return (
    <aside className="flex min-h-[78vh] flex-col overflow-hidden rounded-[28px] border border-white/10 bg-slate-900/75 shadow-2xl shadow-slate-950/40 backdrop-blur-xl xl:h-full xl:min-h-0">
      <div className="border-b border-white/10 px-5 py-4">
        <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Explainability viewer</p>
        <div className="mt-2 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-white">Source document</h2>
            <p className="text-sm text-slate-400">
              Inspect the exact snippet used to justify the current answer.
            </p>
          </div>
          <div
            className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${ROLE_STYLES[role].badge}`}
          >
            {role} visibility
          </div>
        </div>
      </div>

      {selectedSource ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="border-b border-white/10 px-5 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-base font-semibold text-white">{selectedSource.doc}</p>
                <p className="text-sm text-slate-400">
                  {isManualOpen
                    ? `Opened from file search${selectedSource.ownerName ? ` | Owner ${selectedSource.ownerName}` : ''}`
                    : `Page ${selectedSource.page} | Confidence ${selectedSource.confidence}`}
                </p>
              </div>
              <div className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-xs text-slate-200">
                {isManualOpen ? 'Full file preview' : 'Evidence trace'}
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <div className="rounded-[26px] border border-white/10 bg-white/[0.04] p-5 shadow-inner shadow-slate-950/30">
              <div className="mb-5 flex items-center justify-between gap-3 border-b border-white/10 pb-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Highlighted evidence</p>
                  <p className="mt-1 text-sm text-slate-300">{activeDocument.section}</p>
                </div>
                <div className="rounded-full bg-amber-400/15 px-3 py-1 text-xs text-amber-100">
                  Retrieved snippet
                </div>
              </div>

              <div className="space-y-4 text-sm leading-7 text-slate-300">
                {activeDocument.content.map((paragraph) => {
                  const isHighlight = selectedSource.text
                    ? paragraph.includes(selectedSource.text)
                    : false

                  return (
                    <p
                      key={paragraph}
                      className={
                        isHighlight
                          ? 'rounded-2xl border border-amber-300/30 bg-amber-400/[0.12] px-4 py-3 text-slate-50 shadow-lg shadow-amber-950/10'
                          : ''
                      }
                    >
                      {paragraph}
                    </p>
                  )
                })}
              </div>
            </div>

            <div className="mt-5 rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Visible document pool</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {documents.map((document) => (
                  <div
                    key={document.id}
                    className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-xs text-slate-300"
                  >
                    {document.name}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="max-w-md rounded-[28px] border border-dashed border-white/15 bg-white/[0.04] p-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-blue-500/25 to-cyan-400/20 text-sm font-semibold text-blue-100">
              DOC
            </div>
            <h3 className="mt-5 text-xl font-semibold text-white">
              Select a source to view explanation
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              The right panel shows the retrieved document, highlighted evidence, and the source context behind the answer.
            </p>
          </div>
        </div>
      )}
    </aside>
  )
}

export default SourceViewer
