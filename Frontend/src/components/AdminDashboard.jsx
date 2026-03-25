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
    <main className="mt-4 grid flex-1 gap-4 xl:min-h-0 xl:grid-cols-[minmax(0,1.15fr)_minmax(300px,0.85fr)] xl:overflow-hidden">
      <section className="rounded-[28px] border border-white/10 bg-white/[0.07] p-5 shadow-2xl shadow-slate-950/40 backdrop-blur-xl xl:flex xl:min-h-0 xl:flex-col">
        <div className="border-b border-white/10 pb-5">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Admin console</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Manage uploads and visibility</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Admin can upload files, change visibility at any time, and delete any document.
          </p>
        </div>

        <div className="mt-5 space-y-4 xl:min-h-0 xl:flex-1 xl:overflow-y-auto xl:pr-1">
          {documents.map((document) => (
            <div
              key={document.id}
              className="rounded-[24px] border border-white/10 bg-slate-950/50 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-base font-semibold text-white">{document.name}</p>
                    <span className="rounded-full bg-white/[0.06] px-2 py-1 text-[11px] text-slate-300">
                      {document.type}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{document.summary}</p>
                </div>
                <div className="flex items-start gap-2">
                  <div className="text-right text-xs text-slate-400">
                    <p>Owner: {document.ownerName}</p>
                    <p className="mt-1">Uploaded: {document.uploadedAt}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onDeleteDocument(document.id)}
                    className="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-100 transition hover:bg-rose-500/20"
                  >
                    Delete
                  </button>
                </div>
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

      <aside className="flex flex-col gap-4 xl:min-h-0 xl:overflow-hidden">
        <UploadPanel
          currentUser={currentUser}
          uploadVisibilityScope={uploadVisibilityScope}
          onUploadVisibilityChange={onUploadVisibilityChange}
          onFileUpload={onFileUpload}
          totalCount={documents.length}
        />

        <section className="rounded-[28px] border border-white/10 bg-slate-900/75 p-5 shadow-2xl shadow-slate-950/40 backdrop-blur-xl xl:min-h-0 xl:flex-1 xl:overflow-y-auto">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Admin profile</p>
          <h2 className="mt-2 text-xl font-semibold text-white">{currentUser.name}</h2>
          <p className="mt-2 text-sm text-slate-400">
            Full control across all uploaded files, visibility settings, and document deletion.
          </p>

          <div className="mt-5 grid gap-3">
            <div className="rounded-[22px] border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Total files</p>
              <p className="mt-2 text-3xl font-semibold text-white">{documents.length}</p>
            </div>
            <div className="rounded-[22px] border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Private files</p>
              <p className="mt-2 text-3xl font-semibold text-white">
                {documents.filter((document) => document.visibilityScope === 'private').length}
              </p>
            </div>
          </div>
        </section>
      </aside>
    </main>
  )
}

export default AdminDashboard
