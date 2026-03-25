import { DEMO_USERS } from '../data/mockData'

function LoginPage({ form, onChange, onSubmit, error, isSubmitting }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#212121] px-4">
      <section className="w-full max-w-md rounded-3xl border border-white/10 bg-[#171717] p-8 shadow-2xl shadow-black/30">
        <h1 className="text-center text-2xl font-semibold text-white">FindX</h1>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-2 block text-sm text-zinc-300">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(event) => onChange({ email: event.target.value })}
              placeholder="name@findx.ai"
              className="w-full rounded-2xl border border-white/10 bg-[#212121] px-4 py-3 text-sm text-white outline-none transition focus:border-white/20"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-zinc-300">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(event) => onChange({ password: event.target.value })}
              placeholder="Password"
              className="w-full rounded-2xl border border-white/10 bg-[#212121] px-4 py-3 text-sm text-white outline-none transition focus:border-white/20"
            />
          </div>

          {error ? (
            <div className="rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-2xl bg-white px-4 py-3 text-sm font-medium text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-500"
          >
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="mt-6 border-t border-white/10 pt-5">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Demo emails</p>
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
                className="rounded-2xl border border-white/10 bg-[#212121] px-4 py-3 text-left text-sm text-zinc-200 transition hover:bg-[#2a2a2a]"
              >
                {user.email}
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

export default LoginPage
