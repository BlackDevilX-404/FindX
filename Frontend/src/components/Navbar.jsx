function Navbar({ currentUser, onLogout, onNewChat }) {
  return (
    <header className="flex items-center justify-end gap-2 py-2">
      {currentUser.role !== 'Admin' ? (
        <button
          type="button"
          onClick={onNewChat}
          className="rounded-full border border-white/10 bg-[#2f2f2f] px-4 py-2 text-sm text-white transition hover:bg-[#3a3a3a]"
        >
          New chat
        </button>
      ) : null}

      <button
        type="button"
        onClick={onLogout}
        className="rounded-full border border-white/10 bg-[#2f2f2f] px-4 py-2 text-sm text-white transition hover:bg-[#3a3a3a]"
      >
        Logout
      </button>
    </header>
  )
}

export default Navbar
