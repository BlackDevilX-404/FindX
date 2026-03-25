import UploadPanel from './UploadPanel'
import VisibilitySelector from './VisibilitySelector'

function AdminDashboard({
  currentUser,
  documents,
  uploadVisibilityScope,
  onUploadVisibilityChange,
  onFileUpload,
  onDocumentVisibilityChange,
  onDeleteDocument,
}) {
  return (
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
                </div>

                <button
                  type="button"
                  onClick={() => onDeleteDocument(document.id)}
                  className="rounded-full border border-red-400/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-100 transition hover:bg-red-500/20"
                >
                  Delete
                </button>
              </div>

              <div className="mt-4">
                <VisibilitySelector
                  value={document.visibilityScope}
                  onChange={(scope) => onDocumentVisibilityChange(document.id, scope)}
                  title="Visibility"
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      <aside className="flex flex-col gap-4 xl:min-h-0">
        <UploadPanel
          currentUser={currentUser}
          uploadVisibilityScope={uploadVisibilityScope}
          onUploadVisibilityChange={onUploadVisibilityChange}
          onFileUpload={onFileUpload}
          totalCount={documents.length}
        />

        <section className="rounded-3xl border border-white/10 bg-[#171717] p-4">
          <h2 className="text-sm font-medium text-white">{currentUser.name}</h2>
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
  )
}

export default AdminDashboard
