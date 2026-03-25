import { ROLE_STYLES, ROLES } from '../data/mockData'

function RoleSelector({ role, onRoleChange }) {
  return (
    <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200">
      <span className="text-slate-400">Role</span>
      <select
        value={role}
        onChange={(event) => onRoleChange(event.target.value)}
        className={`rounded-xl border px-3 py-2 font-medium outline-none transition ${ROLE_STYLES[role].select}`}
      >
        {ROLES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

export default RoleSelector
