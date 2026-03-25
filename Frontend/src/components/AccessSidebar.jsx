import { useMemo, useState } from 'react'
import { formatConversationTime, getVisibilityLabel } from '../data/mockData'
import UploadPanel from './UploadPanel'

function AccessSidebar({
  currentUser,
  documents,
  conversations,
  activeConversationId,
  onConversationSelect,
  onNewChat,
  uploadVisibilityScope,
  onUploadVisibilityChange,
  onFileUpload,
  onOpenDocument,
}) {
  const [panelMode, setPanelMode] = useState('history')
  const [searchDraft, setSearchDraft] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredDocuments = useMemo(() => {
    const normalized = searchQuery.trim().toLowerCase()
    if (!normalized) {
      return documents
    }

    return documents.filter((document) => {
      const haystack = `${document.name} ${document.summary} ${document.ownerName}`.toLowerCase()
      return haystack.includes(normalized)
    })
  }, [documents, searchQuery])

  const handleSearchSubmit = (event) => {
    event.preventDefault()
    setSearchQuery(searchDraft)
  }

  return (
    <aside className="grid min-h-[78vh] gap-4 rounded-[28px] border border-white/10 bg-slate-900/75 p-4 shadow-2xl shadow-slate-950/40 backdrop-blur-xl xl:h-full xl:min-h-0 xl:grid-rows-[minmax(0,1fr)_auto] xl:overflow-hidden">
      <div className="flex min-h-0 flex-col rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Workspace tools</p>
            <h2 className="mt-2 text-lg font-semibold text-white">History and file search</h2>
          </div>
          {panelMode === 'history' ? (
            <button
              type="button"
              onClick={onNewChat}
              className="rounded-full border border-blue-300/30 bg-blue-500/10 px-3 py-2 text-xs font-medium text-blue-100 transition hover:bg-blue-500/20"
            >
              New chat
            </button>
          ) : null}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 rounded-2xl border border-white/10 bg-slate-950/40 p-1">
          <button
            type="button"
            onClick={() => setPanelMode('history')}
            className={`rounded-xl px-3 py-2 text-sm transition ${
              panelMode === 'history'
                ? 'bg-blue-500/15 text-blue-100'
                : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-200'
            }`}
          >
            Search history
          </button>
          <button
            type="button"
            onClick={() => setPanelMode('files')}
            className={`rounded-xl px-3 py-2 text-sm transition ${
              panelMode === 'files'
                ? 'bg-blue-500/15 text-blue-100'
                : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-200'
            }`}
          >
            Search files
          </button>
        </div>

        {panelMode === 'history' ? (
          <div className="mt-4 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => onConversationSelect(conversation.id)}
                className={`block w-full rounded-2xl border px-3 py-3 text-left transition ${
                  conversation.id === activeConversationId
                    ? 'border-blue-300/40 bg-blue-500/10'
                    : 'border-white/10 bg-white/[0.03] hover:bg-white/[0.06]'
                }`}
              >
                <p className="truncate text-sm font-medium text-white">{conversation.title}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {formatConversationTime(conversation.updatedAt)}
                </p>
              </button>
            ))}
          </div>
        ) : (
          <div className="mt-4 min-h-0 flex flex-1 flex-col">
            <form onSubmit={handleSearchSubmit} className="flex gap-2">
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Search accessible files"
                className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-300/40"
              />
              <button
                type="submit"
                className="rounded-2xl border border-blue-300/30 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-100 transition hover:bg-blue-500/20"
              >
                Search
              </button>
            </form>

            <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
              {filteredDocuments.map((document) => (
                <div
                  key={document.id}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">{document.name}</p>
                      <p className="mt-1 text-xs text-slate-400">Owner: {document.ownerName}</p>
                    </div>
                    <span className="rounded-full bg-white/[0.06] px-2 py-1 text-[11px] text-slate-300">
                      {document.type}
                    </span>
                  </div>

                  <p className="mt-2 text-xs leading-5 text-slate-400">{document.summary}</p>

                  <div className="mt-3 flex items-center justify-between gap-3">
                    <div className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] text-slate-300">
                      {getVisibilityLabel(document.visibilityScope)}
                    </div>
                    <button
                      type="button"
                      onClick={() => onOpenDocument(document)}
                      className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs text-slate-200 transition hover:bg-white/[0.1]"
                    >
                      Open file
                    </button>
                  </div>
                </div>
              ))}

              {!filteredDocuments.length ? (
                <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] px-4 py-6 text-sm text-slate-400">
                  No files match this search.
                </div>
              ) : null}
            </div>
          </div>
        )}
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
