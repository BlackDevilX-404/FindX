function CitationChip({ source, isActive, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-2 text-xs font-medium transition ${
        isActive
          ? 'border-blue-300/60 bg-blue-500/20 text-blue-50 shadow-md shadow-blue-950/30'
          : 'border-white/10 bg-white/5 text-slate-200 hover:border-blue-300/40 hover:bg-blue-500/10'
      }`}
    >
      {source.doc} - Page {source.page}
    </button>
  )
}

export default CitationChip
