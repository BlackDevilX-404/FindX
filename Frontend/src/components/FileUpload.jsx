function FileUpload({ onFileUpload, uploadedFiles, label = 'Upload document' }) {
  return (
    <div className="flex items-center gap-3">
      <label className="group inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-blue-400/30 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-100 transition hover:border-blue-300/60 hover:bg-blue-500/20">
        <span className="text-base">+</span>
        {label}
        <input
          type="file"
          multiple
          accept=".pdf,.ppt,.pptx"
          onChange={onFileUpload}
          className="hidden"
        />
      </label>

      <div className="hidden items-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100 md:inline-flex">
        <span className="h-2 w-2 rounded-full bg-emerald-400" />
        {uploadedFiles.length} files indexed
      </div>
    </div>
  )
}

export default FileUpload
