import { getVisibilityLabel } from '../data/mockData'

function UploadPanel({
  currentUser,
  onFileUpload,
  totalCount,
}) {
  const isAdmin = currentUser.role === 'Admin'

  return (
    <section className="rounded-2xl border border-white/10 bg-[#171717] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-white">Content ingest</h2>
          <p className="mt-1 text-xs text-zinc-500">{totalCount} files</p>
        </div>
      </div>

      {isAdmin ? (
        <>
          <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-[#2f2f2f] px-4 py-2 text-sm text-white transition hover:bg-[#3a3a3a]">
            <span>+</span>
            Upload file
            <input
              type="file"
              multiple
              accept=".pdf,.ppt,.pptx,.docx,.txt,.md,.csv,.json,.xlsx"
              onChange={onFileUpload}
              className="hidden"
            />
          </label>
        </>
      ) : (
        <div className="mt-4 rounded-2xl border border-white/10 bg-[#212121] px-4 py-3 text-sm text-zinc-300">
          Admin only. Visibility is chosen after file selection. <span className="text-white">{getVisibilityLabel('private')}</span>
        </div>
      )}
    </section>
  )
}

export default UploadPanel
