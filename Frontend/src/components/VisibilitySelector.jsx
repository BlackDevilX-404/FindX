import { VISIBILITY_OPTIONS } from '../data/mockData'

function VisibilitySelector({
  value,
  onChange,
  title = 'Visibility',
  interactive = true,
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">{title}</p>
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
                  ? 'border-white/20 bg-[#2f2f2f] text-white'
                  : 'border-white/10 bg-[#212121] text-zinc-300'
              } ${interactive ? 'hover:bg-[#2a2a2a]' : 'cursor-not-allowed opacity-70'}`}
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
