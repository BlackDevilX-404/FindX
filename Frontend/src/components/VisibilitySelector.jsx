import { VISIBILITY_OPTIONS } from '../data/mockData'

function VisibilitySelector({
  value,
  onChange,
  title = 'Visibility',
  interactive = true,
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{title}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {VISIBILITY_OPTIONS.map((option) => {
          const isActive = value === option.id

          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onChange(option.id)}
              disabled={!interactive}
              className={`rounded-full border px-3 py-2 text-xs transition ${
                isActive
                  ? 'border-blue-300/40 bg-blue-500/10 text-blue-100'
                  : 'border-white/10 bg-white/[0.04] text-slate-300'
              } ${interactive ? 'hover:bg-white/[0.08]' : 'cursor-not-allowed opacity-80'}`}
            >
              {option.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default VisibilitySelector
