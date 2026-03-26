function Navbar({ currentUser, onLogout, onNewChat }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 py-2">
      <div>
        <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--text-muted)]">Enterprise search</p>
        <h1 className="mt-1 text-lg font-semibold text-[var(--text-main)]">FindX workspace</h1>
      </div>

      <div className="flex items-center gap-2">
      {currentUser.role !== 'Admin' ? (
        <button
          type="button"
          onClick={onNewChat}
          className="rounded-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-2 text-sm text-[var(--text-main)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]"
        >
          New chat
        </button>
      ) : null}

      <button
        type="button"
        onClick={onLogout}
        className="rounded-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-2 text-sm text-[var(--text-main)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]"
      >
        Logout
      </button>
      </div>
    </header>
  )
}

export default Navbar
