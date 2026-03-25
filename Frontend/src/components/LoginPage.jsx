import { DEMO_USERS } from '../data/mockData'

function LoginPage({ form, onChange, onSubmit, error, isSubmitting }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-0 h-72 w-72 -translate-x-1/2 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute bottom-0 left-[-8rem] h-80 w-80 rounded-full bg-cyan-400/10 blur-3xl" />
      </div>

      <section className="relative w-full max-w-md rounded-[32px] border border-white/10 bg-slate-950/80 p-8 shadow-2xl shadow-slate-950/40">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 via-indigo-500 to-cyan-400 text-lg font-semibold text-white">
          FX
        </div>
        <h1 className="mt-5 text-center text-3xl font-semibold text-white">FindX</h1>
        <p className="mt-2 text-center text-sm text-slate-400">
          Sign in to continue to your workspace.
        </p>

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <div>
            <label className="mb-2 block text-sm text-slate-300">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(event) => onChange({ email: event.target.value })}
              placeholder="name@findx.ai"
              className="w-full rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-blue-300/50"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-slate-300">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(event) => onChange({ password: event.target.value })}
              placeholder="Enter password"
              className="w-full rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-blue-300/50"
            />
          </div>

          {error ? (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-2xl bg-gradient-to-r from-blue-500 via-indigo-500 to-cyan-400 px-4 py-3 text-sm font-semibold text-white shadow-xl shadow-blue-950/40 transition hover:opacity-95"
          >
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="mt-6 rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Demo accounts</p>
          <div className="mt-3 space-y-2">
            {DEMO_USERS.map((user) => (
              <button
                key={user.id}
                type="button"
                onClick={() =>
                  onChange({
                    email: user.email,
                    password: user.password,
                  })
                }
                className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-3 text-left transition hover:bg-white/[0.07]"
              >
                <div>
                  <p className="text-sm font-medium text-white">{user.name}</p>
                  <p className="text-xs text-slate-400">{user.role}</p>
                </div>
                <p className="text-xs text-slate-400">{user.email}</p>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

export default LoginPage
