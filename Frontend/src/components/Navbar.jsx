function Navbar({ currentUser, onLogout, onNewChat }) {
  return (
    <header className="rounded-[28px] border border-white/10 bg-slate-900/70 px-4 py-3 shadow-xl shadow-slate-950/30 backdrop-blur-xl sm:px-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 via-indigo-500 to-cyan-400 shadow-lg shadow-blue-950/40">
            <span className="text-lg font-semibold text-white">FX</span>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
              FindX
            </p>
            <p className="text-sm text-slate-300">
              {currentUser.role === 'Admin'
                ? 'Admin workspace for uploads, visibility, and delete control'
                : 'Secure document search with personal chat history'}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {currentUser.role !== 'Admin' ? (
            <button
              type="button"
              onClick={onNewChat}
              className="rounded-2xl border border-blue-300/30 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-100 transition hover:bg-blue-500/20"
            >
              New chat
            </button>
          ) : null}

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-200">
            <p className="font-medium text-white">{currentUser.name}</p>
            <p className="text-xs text-slate-400">
              {currentUser.email} | {currentUser.role}
            </p>
          </div>

          <button
            type="button"
            onClick={onLogout}
            className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-200 transition hover:bg-white/[0.08]"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  )
}

export default Navbar
