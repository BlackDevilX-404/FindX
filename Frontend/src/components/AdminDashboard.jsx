import { useState } from 'react'
import { getVisibilityLabel } from '../data/mockData'
import UploadPanel from './UploadPanel'
import VisibilitySelector from './VisibilitySelector'

function AdminDashboard({
  currentUser,
  documents,
  onFileUpload,
  onDocumentVisibilityChange,
  onDeleteDocument,
}) {
  const displayName = currentUser.name ?? currentUser.username ?? currentUser.email ?? 'Admin'
  const [visibilityModalDocument, setVisibilityModalDocument] = useState(null)

  const handleOpenVisibilityModal = (document) => {
    setVisibilityModalDocument(document)
  }

  const handleCloseVisibilityModal = () => {
    setVisibilityModalDocument(null)
  }

  const handleChangeVisibility = async (scope) => {
    if (!visibilityModalDocument) {
      return
    }

    await onDocumentVisibilityChange(visibilityModalDocument.id, scope)
    setVisibilityModalDocument(null)
  }

  return (
    <>
      <main className="mt-4 grid flex-1 gap-4 xl:min-h-0 xl:grid-cols-[minmax(0,1fr)_320px] xl:overflow-hidden">
      <section className="flex flex-col rounded-3xl border border-white/10 bg-[#171717] p-4 xl:min-h-0">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-xl font-medium text-white">Documents</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Manage uploaded files and their visibility.
          </p>
        </div>

        <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
          {documents.map((document) => (
            <div
              key={document.id}
              className="rounded-2xl border border-white/10 bg-[#212121] p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-medium text-white">{document.name}</p>
                    <span className="rounded-full border border-white/10 bg-[#171717] px-2 py-1 text-[11px] text-zinc-400">
                      {document.type}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-zinc-400">{document.summary}</p>
                  <p className="mt-2 text-xs text-zinc-500">
                    Owner: {document.ownerName} | Uploaded: {document.uploadedAt}
                  </p>
                  <div className="mt-4 rounded-2xl border border-white/10 bg-[#171717] px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Current visibility</p>
                    <p className="mt-2 text-sm text-white">{getVisibilityLabel(document.visibilityScope)}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleOpenVisibilityModal(document)}
                    className="rounded-full border border-white/10 bg-[#171717] px-3 py-1.5 text-xs text-zinc-200 transition hover:bg-[#2a2a2a]"
                  >
                    Change visibility
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteDocument(document.id)}
                    className="rounded-full border border-red-400/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-100 transition hover:bg-red-500/20"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <aside className="flex flex-col gap-4 xl:min-h-0">
        <UploadPanel
          currentUser={currentUser}
          onFileUpload={onFileUpload}
          totalCount={documents.length}
        />

        <section className="rounded-3xl border border-white/10 bg-[#171717] p-4">
          <h2 className="text-sm font-medium text-white">{displayName}</h2>
          <p className="mt-2 text-sm text-zinc-400">
            Admin access for document upload, visibility control, and cleanup.
          </p>

          <div className="mt-4 space-y-3">
            <div className="rounded-2xl border border-white/10 bg-[#212121] p-4">
              <p className="text-xs text-zinc-500">Total files</p>
              <p className="mt-2 text-2xl font-medium text-white">{documents.length}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-[#212121] p-4">
              <p className="text-xs text-zinc-500">Private files</p>
              <p className="mt-2 text-2xl font-medium text-white">
                {documents.filter((document) => document.visibilityScope === 'private').length}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-[#212121] p-4">
              <p className="text-xs text-zinc-500">Shared files</p>
              <p className="mt-2 text-2xl font-medium text-white">
                {documents.filter((document) => document.visibilityScope === 'both').length}
              </p>
            </div>
          </div>
        </section>
      </aside>
      </main>

      {visibilityModalDocument ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 px-4">
          <div className="w-full max-w-md rounded-3xl border border-white/10 bg-[#171717] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
            <h2 className="text-base font-medium text-white">Change Visibility</h2>
            <p className="mt-2 text-sm text-zinc-400">
              Update who can access <span className="text-white">{visibilityModalDocument.name}</span>.
            </p>

            <div className="mt-4 rounded-2xl border border-white/10 bg-[#212121] px-4 py-3 text-sm text-zinc-300">
              <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Current visibility</p>
              <p className="mt-2 text-white">{getVisibilityLabel(visibilityModalDocument.visibilityScope)}</p>
            </div>

            <div className="mt-4">
              <VisibilitySelector
                value={visibilityModalDocument.visibilityScope}
                onChange={handleChangeVisibility}
                title="Choose new visibility"
              />
            </div>

            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={handleCloseVisibilityModal}
                className="rounded-full border border-white/10 bg-[#212121] px-4 py-2 text-sm text-zinc-300 transition hover:bg-[#2a2a2a]"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

export default AdminDashboard
