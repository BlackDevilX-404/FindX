function CitationChip({ source, isActive, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-2 text-xs transition ${
        isActive
          ? 'border-white/20 bg-[#3a3a3a] text-white'
          : 'border-white/10 bg-[#2a2a2a] text-zinc-300 hover:bg-[#343434]'
      }`}
    >
      {source.doc}
      {source.page ? ` • p.${source.page}` : ''}
    </button>
  )
}

export default CitationChip
