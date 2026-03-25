import { getVisibilityLabel } from '../data/mockData'
import VisibilitySelector from './VisibilitySelector'

function UploadPanel({
  currentUser,
  uploadVisibilityScope,
  onUploadVisibilityChange,
  onFileUpload,
  totalCount,
}) {
  return (
    <section className="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Upload</p>
          <h2 className="mt-2 text-lg font-semibold text-white">Share files in FindX</h2>
        </div>
        <div className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs text-slate-300">
          {totalCount} files
        </div>
      </div>

      <p className="mt-2 text-sm leading-6 text-slate-400">
        {currentUser.role === 'Admin'
          ? 'Admin can upload files, set visibility before upload, and update access at any time.'
          : 'Uploads from your account use a fixed visibility scope. Only admin can change access or delete files.'}
      </p>

      {currentUser.role === 'Admin' ? (
        <div className="mt-4">
          <VisibilitySelector
            value={uploadVisibilityScope}
            onChange={onUploadVisibilityChange}
            title="Choose visibility before upload"
          />
        </div>
      ) : (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
          Default visibility: <span className="font-medium text-white">{getVisibilityLabel(uploadVisibilityScope)}</span>
        </div>
      )}

      <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-blue-400/30 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-100 transition hover:border-blue-300/60 hover:bg-blue-500/20">
        <span className="text-base">+</span>
        Upload file
        <input
          type="file"
          multiple
          accept=".pdf,.ppt,.pptx"
          onChange={onFileUpload}
          className="hidden"
        />
      </label>
    </section>
  )
}

export default UploadPanel
