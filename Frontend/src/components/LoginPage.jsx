import { DEMO_USERS } from '../data/mockData'

function LoginPage({ form, onChange, onSubmit, error, isSubmitting }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-8">
      <section className="w-full max-w-md rounded-[32px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-8 shadow-[0_24px_70px_rgba(0,0,0,0.35)] backdrop-blur">
        <div className="text-center">
          <p className="text-[11px] uppercase tracking-[0.35em] text-[var(--text-muted)]">FindX Workspace</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--text-main)]">FindX</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">
            Sign in to search the documents your role is allowed to access.
          </p>
        </div>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-2 block text-sm text-[var(--text-muted)]">Work email</label>
            <input
              type="email"
              value={form.email}
              onChange={(event) => onChange({ email: event.target.value })}
              placeholder="name@findx.ai"
              className="w-full rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-main)] outline-none placeholder:text-[var(--text-muted)]/70 focus:border-[var(--border-strong)] focus:shadow-[0_0_0_4px_rgba(201,141,88,0.12)]"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-[var(--text-muted)]">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(event) => onChange({ password: event.target.value })}
              placeholder="Password"
              className="w-full rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-main)] outline-none placeholder:text-[var(--text-muted)]/70 focus:border-[var(--border-strong)] focus:shadow-[0_0_0_4px_rgba(201,141,88,0.12)]"
            />
          </div>

          {error ? (
            <div className="rounded-2xl border border-red-400/20 bg-red-500/12 px-4 py-3 text-sm text-red-100">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-2xl bg-[var(--text-main)] px-4 py-3 text-sm font-semibold text-[#16120e] shadow-[0_16px_32px_rgba(0,0,0,0.18)] hover:bg-[#fff8ef] disabled:cursor-not-allowed disabled:bg-zinc-500"
          >
            {isSubmitting ? 'Signing in...' : 'Enter workspace'}
          </button>
        </form>

        <div className="mt-6 border-t border-[var(--border-soft)] pt-5">
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">Demo accounts</p>
          <div className="mt-3 flex flex-col gap-2">
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
                className="rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3 text-left text-sm text-[var(--text-main)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]"
              >
                <span className="block">{user.email}</span>
                <span className="mt-1 block text-xs text-[var(--text-muted)]">{user.role} access</span>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

export default LoginPage
