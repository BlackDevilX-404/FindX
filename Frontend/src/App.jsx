import { useEffect, useRef, useState } from 'react'
import AccessSidebar from './components/AccessSidebar'
import AdminDashboard from './components/AdminDashboard'
import ChatWindow from './components/ChatWindow'
import InputBox from './components/InputBox'
import {
  clearStoredToken,
  fetchCurrentUser,
  getStoredToken,
  loginUser,
  sendChatMessage,
  storeToken,
  uploadFileToSession,
} from './lib/api'
import LoginPage from './components/LoginPage'
import Navbar from './components/Navbar'
import SourceViewer from './components/SourceViewer'
import {
  INITIAL_DOCUMENTS,
  SUGGESTED_QUERIES,
  canDeleteDocument,
  canEditDocumentVisibility,
  createConversation,
  getAccessibleDocuments,
  getDefaultUploadVisibility,
  normalizeVisibilityScope,
} from './data/mockData'

const DOCUMENTS_KEY = 'findx-documents'
const CHAT_STORE_KEY = 'findx-chat-store'
const SIDEBAR_COLLAPSED_KEY = 'findx-sidebar-collapsed'

const defaultLoginForm = {
  email: '',
  password: '',
}

function readStorage(key, fallback) {
  try {
    const stored = window.localStorage.getItem(key)
    return stored ? JSON.parse(stored) : fallback
  } catch {
    return fallback
  }
}

function sortConversations(conversations) {
  return [...conversations].sort(
    (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
  )
}

function normalizeDocuments(documents) {
  return documents.map((document) => {
    if (document.visibilityScope) {
      return {
        ...document,
        visibilityScope: normalizeVisibilityScope(document.visibilityScope),
      }
    }

    if (Array.isArray(document.visibleTo)) {
      const hasHr = document.visibleTo.includes('hr-user')
      const hasEmployee = document.visibleTo.includes('employee-user')
      const visibilityScope = hasHr && hasEmployee ? 'both' : hasHr ? 'hr' : hasEmployee ? 'employee' : 'private'
      const { visibleTo, ...rest } = document

      return {
        ...rest,
        visibilityScope,
      }
    }

    return {
      ...document,
      visibilityScope: 'private',
    }
  })
}

function formatChatHistory(messages) {
  return messages
    .filter((message) => message.type === 'user' || message.kind === 'response')
    .map((message) => ({
      role: message.type === 'user' ? 'user' : 'assistant',
      content: message.text,
    }))
}

function getBackendSessionId(user) {
  return user?.id ?? ''
}

function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [documents, setDocuments] = useState(() =>
    normalizeDocuments(readStorage(DOCUMENTS_KEY, INITIAL_DOCUMENTS)),
  )
  const [authToken, setAuthToken] = useState(() => getStoredToken())
  const [chatStore, setChatStore] = useState(() => readStorage(CHAT_STORE_KEY, {}))
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [selectedSource, setSelectedSource] = useState(null)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isAuthLoading, setIsAuthLoading] = useState(() => Boolean(getStoredToken()))
  const [isSubmittingLogin, setIsSubmittingLogin] = useState(false)
  const [loginForm, setLoginForm] = useState(defaultLoginForm)
  const [loginError, setLoginError] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [uploadVisibilityScope, setUploadVisibilityScope] = useState('private')
  const [isUploading, setIsUploading] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() =>
    readStorage(SIDEBAR_COLLAPSED_KEY, false),
  )
  const chatViewportRef = useRef(null)

  const userKey = currentUser?.email.toLowerCase() ?? null
  const conversations = userKey ? chatStore[userKey] ?? [] : []
  const accessibleDocuments = currentUser
    ? getAccessibleDocuments(documents, currentUser)
    : []
  const activeConversation =
    currentUser && currentUser.role !== 'Admin'
      ? conversations.find((conversation) => conversation.id === activeConversationId) ??
        conversations[0] ??
        null
      : null
  useEffect(() => {
    window.localStorage.setItem(DOCUMENTS_KEY, JSON.stringify(documents))
  }, [documents])

  useEffect(() => {
    window.localStorage.setItem(CHAT_STORE_KEY, JSON.stringify(chatStore))
  }, [chatStore])

  useEffect(() => {
    window.localStorage.setItem(
      SIDEBAR_COLLAPSED_KEY,
      JSON.stringify(isSidebarCollapsed),
    )
  }, [isSidebarCollapsed])

  useEffect(() => {
    setUploadVisibilityScope(currentUser ? getDefaultUploadVisibility(currentUser) : 'private')
  }, [currentUser])

  useEffect(() => {
    if (!authToken) {
      setCurrentUser(null)
      setIsAuthLoading(false)
      return
    }

    let isCancelled = false

    const loadCurrentUser = async () => {
      setIsAuthLoading(true)

      try {
        const user = await fetchCurrentUser(authToken)

        if (!isCancelled) {
          setCurrentUser(user)
          setLoginError('')
        }
      } catch (error) {
        if (!isCancelled) {
          clearStoredToken()
          setAuthToken('')
          setCurrentUser(null)
          setLoginError('Your session expired. Please sign in again.')
        }
      } finally {
        if (!isCancelled) {
          setIsAuthLoading(false)
        }
      }
    }

    loadCurrentUser()

    return () => {
      isCancelled = true
    }
  }, [authToken])

  useEffect(() => {
    if (!currentUser || currentUser.role === 'Admin' || !userKey) {
      setActiveConversationId(null)
      return
    }

    const userConversations = chatStore[userKey] ?? []

    if (!userConversations.length) {
      const starterConversation = createConversation(currentUser)
      setChatStore((current) => ({
        ...current,
        [userKey]: [starterConversation],
      }))
      setActiveConversationId(starterConversation.id)
      return
    }

    if (!userConversations.some((conversation) => conversation.id === activeConversationId)) {
      setActiveConversationId(userConversations[0].id)
    }
  }, [activeConversationId, chatStore, currentUser, userKey])

  useEffect(() => {
    if (!chatViewportRef.current) {
      return
    }

    chatViewportRef.current.scrollTo({
      top: chatViewportRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [activeConversation?.messages?.length, activeConversationId, isTyping])

  useEffect(() => {
    if (!activeConversation) {
      setSelectedSource(null)
      return
    }

    const latestSourcedMessage = [...activeConversation.messages]
      .reverse()
      .find((message) => message.sources?.length)

    setSelectedSource(latestSourcedMessage?.sources[0] ?? null)
  }, [activeConversationId, activeConversation])

  const updateUserConversations = (updater) => {
    if (!userKey) {
      return
    }

    setChatStore((current) => {
      const existing = current[userKey] ?? []
      return {
        ...current,
        [userKey]: sortConversations(updater(existing)),
      }
    })
  }

  const handleLoginChange = (partialForm) => {
    setLoginError('')
    setLoginForm((current) => ({
      ...current,
      ...partialForm,
    }))
  }

  const handleLogin = async (event) => {
    event.preventDefault()
    setIsSubmittingLogin(true)

    try {
      const response = await loginUser(loginForm.email.trim(), loginForm.password.trim())

      storeToken(response.access_token)
      setAuthToken(response.access_token)
      setCurrentUser(response.user)
      setInput('')
      setSelectedSource(null)
      setIsTyping(false)
      setLoginError('')
      setUploadError('')
    } catch (error) {
      setLoginError(error.message)
    } finally {
      setIsSubmittingLogin(false)
    }
  }

  const handleLogout = () => {
    clearStoredToken()
    setAuthToken('')
    setCurrentUser(null)
    setActiveConversationId(null)
    setSelectedSource(null)
    setInput('')
    setIsTyping(false)
    setUploadError('')
    setLoginForm(defaultLoginForm)
  }

  const handleNewChat = () => {
    if (!currentUser || currentUser.role === 'Admin') {
      return
    }

    const newConversation = createConversation(currentUser)
    updateUserConversations((existing) => [newConversation, ...existing])
    setActiveConversationId(newConversation.id)
    setSelectedSource(null)
    setInput('')
  }

  const ensureConversation = () => {
    if (activeConversation) {
      return activeConversation.id
    }

    const newConversation = createConversation(currentUser)
    updateUserConversations((existing) => [newConversation, ...existing])
    setActiveConversationId(newConversation.id)
    return newConversation.id
  }

  const handleSubmit = async (value) => {
    if (!currentUser || currentUser.role === 'Admin' || !authToken) {
      return
    }

    const query = value.trim()
    if (!query || isTyping) {
      return
    }

    const conversationId = ensureConversation()
    const existingConversation =
      (chatStore[userKey] ?? []).find((conversation) => conversation.id === conversationId) ??
      null
    const submittedAt = new Date().toISOString()
    const userMessage = {
      id: crypto.randomUUID(),
      type: 'user',
      text: query,
      createdAt: submittedAt,
    }

    setInput('')
    updateUserConversations((existing) =>
      existing.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              title:
                conversation.title === 'New chat'
                  ? query.slice(0, 48)
                  : conversation.title,
              updatedAt: submittedAt,
              messages: [...conversation.messages, userMessage],
            }
          : conversation,
      ),
    )

    setIsTyping(true)

    try {
      const response = await sendChatMessage({
        token: authToken,
        query,
        chatId: getBackendSessionId(currentUser),
        chatHistory: formatChatHistory(existingConversation?.messages ?? []),
      })

      const assistantMessage = {
        id: crypto.randomUUID(),
        type: 'assistant',
        kind: 'response',
        text: response.answer,
        explanation: 'This answer was returned by the live backend search service.',
        sources: [],
        createdAt: new Date().toISOString(),
      }

      updateUserConversations((existing) =>
        existing.map((conversation) =>
          conversation.id === conversationId
            ? {
                ...conversation,
                updatedAt: assistantMessage.createdAt,
                messages: [...conversation.messages, assistantMessage],
              }
            : conversation,
        ),
      )
      setSelectedSource(null)
    } catch (error) {
      const errorMessage = {
        id: crypto.randomUUID(),
        type: 'assistant',
        kind: 'response',
        text: error.message || 'The backend could not answer this query.',
        explanation: 'The request reached the server but did not complete successfully.',
        sources: [],
        createdAt: new Date().toISOString(),
      }

      updateUserConversations((existing) =>
        existing.map((conversation) =>
          conversation.id === conversationId
            ? {
                ...conversation,
                updatedAt: errorMessage.createdAt,
                messages: [...conversation.messages, errorMessage],
              }
            : conversation,
        ),
      )
    } finally {
      setIsTyping(false)
    }
  }

  const handleUploadVisibilityChange = (scope) => {
    setUploadVisibilityScope(scope)
  }

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files ?? [])

    if (!files.length || !currentUser || !authToken) {
      return
    }

    setUploadError('')
    setIsUploading(true)

    try {
      const results = await Promise.all(
        files.map((file) =>
          uploadFileToSession({
            token: authToken,
            sessionId: getBackendSessionId(currentUser),
            file,
          }),
        ),
      )

      const nextDocuments = results
        .map((result) => result.document)
        .filter(Boolean)
        .map((document) => ({
          ...document,
          uploadedAt: 'Just now',
          visibilityScope: normalizeVisibilityScope(document.visibilityScope),
        }))

      if (nextDocuments.length) {
        setDocuments((current) => [...nextDocuments, ...current])
      }
    } catch (error) {
      setUploadError(error.message || 'Upload failed.')
    } finally {
      setIsUploading(false)
    }

    event.target.value = ''
  }

  const handleDocumentVisibilityChange = (documentId, scope) => {
    if (!currentUser) {
      return
    }

    setDocuments((current) =>
      current.map((document) => {
        if (document.id !== documentId || !canEditDocumentVisibility(document, currentUser)) {
          return document
        }

        return {
          ...document,
          visibilityScope: normalizeVisibilityScope(scope),
        }
      }),
    )
  }

  const handleDeleteDocument = (documentId) => {
    const target = documents.find((document) => document.id === documentId)

    if (!target || !canDeleteDocument(target, currentUser)) {
      return
    }

    setDocuments((current) => current.filter((document) => document.id !== documentId))

    if (selectedSource?.doc === target.name) {
      setSelectedSource(null)
    }
  }

  const handleOpenDocument = (document) => {
    setSelectedSource({
      id: `open-${document.id}`,
      doc: document.name,
      page: null,
      confidence: null,
      text: '',
      mode: 'document',
      summary: document.summary,
      ownerName: document.ownerName,
    })
  }

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((current) => !current)
  }

  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <div className="flex min-h-screen items-center justify-center px-4 text-sm text-slate-400">
          Restoring your FindX session...
        </div>
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <LoginPage
          form={loginForm}
          onChange={handleLoginChange}
          onSubmit={handleLogin}
          error={loginError}
          isSubmitting={isSubmittingLogin}
        />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 xl:h-[100dvh] xl:overflow-hidden">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.25),_transparent_58%)]" />
        <div className="absolute right-[-10%] top-1/4 h-80 w-80 rounded-full bg-cyan-400/10 blur-3xl" />
        <div className="absolute left-[-10%] bottom-0 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8 xl:h-[100dvh] xl:min-h-0">
        <Navbar
          currentUser={currentUser}
          onLogout={handleLogout}
          onNewChat={handleNewChat}
        />

        {uploadError ? (
          <div className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {uploadError}
          </div>
        ) : null}

        {isUploading ? (
          <div className="mt-4 rounded-2xl border border-blue-400/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-100">
            Uploading and indexing PDF/PPT files...
          </div>
        ) : null}

        {currentUser.role === 'Admin' ? (
          <AdminDashboard
            currentUser={currentUser}
            documents={documents}
            uploadVisibilityScope={uploadVisibilityScope}
            onUploadVisibilityChange={handleUploadVisibilityChange}
            onFileUpload={handleFileUpload}
            onDocumentVisibilityChange={handleDocumentVisibilityChange}
            onDeleteDocument={handleDeleteDocument}
          />
        ) : (
          <main
            className={`mt-4 grid flex-1 gap-4 xl:min-h-0 xl:overflow-hidden xl:transition-all xl:duration-300 ${
              isSidebarCollapsed
                ? 'xl:grid-cols-[40px_minmax(0,1fr)_minmax(300px,360px)] 2xl:grid-cols-[40px_minmax(0,1fr)_minmax(340px,420px)]'
                : 'xl:grid-cols-[minmax(280px,320px)_minmax(0,1fr)_minmax(300px,360px)] 2xl:grid-cols-[minmax(300px,360px)_minmax(0,1fr)_minmax(340px,420px)]'
            }`}
          >
            <div className="relative min-h-[78vh] xl:min-h-0">
              <button
                type="button"
                onClick={handleToggleSidebar}
                className={`hidden xl:flex absolute top-1/2 z-20 h-14 w-8 items-center justify-center rounded-full border border-white/10 bg-slate-900/90 text-sm font-semibold text-slate-200 shadow-lg shadow-slate-950/40 transition hover:bg-slate-800 ${
                  isSidebarCollapsed
                    ? 'left-1/2 -translate-x-1/2 -translate-y-1/2'
                    : 'right-[-16px] -translate-y-1/2'
                }`}
                aria-label={isSidebarCollapsed ? 'Show tools sidebar' : 'Hide tools sidebar'}
                title={isSidebarCollapsed ? 'Show tools sidebar' : 'Hide tools sidebar'}
              >
                {isSidebarCollapsed ? '>' : '<'}
              </button>

              <div
                className={`h-full transition-all duration-300 ease-out ${
                  isSidebarCollapsed
                    ? 'xl:pointer-events-none xl:absolute xl:inset-y-0 xl:left-0 xl:w-[320px] xl:-translate-x-[calc(100%+0.75rem)] xl:opacity-0'
                    : 'xl:h-full xl:translate-x-0 xl:opacity-100'
                }`}
              >
                <AccessSidebar
                  currentUser={currentUser}
                  documents={accessibleDocuments}
                  conversations={conversations}
                  activeConversationId={activeConversation?.id}
                  onConversationSelect={setActiveConversationId}
                  onNewChat={handleNewChat}
                  uploadVisibilityScope={uploadVisibilityScope}
                  onUploadVisibilityChange={handleUploadVisibilityChange}
                  onFileUpload={handleFileUpload}
                  onOpenDocument={handleOpenDocument}
                />
              </div>
            </div>

            <section className="flex min-h-[78vh] flex-col overflow-hidden rounded-[28px] border border-white/10 bg-white/[0.08] shadow-2xl shadow-slate-950/40 backdrop-blur-xl xl:h-full xl:min-h-0">
              <div className="border-b border-white/10 px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
                      FindX chat
                    </p>
                    <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white">
                      Search only across files visible to your account
                    </h1>
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-sm text-slate-300">
                    {accessibleDocuments.length} accessible files
                  </div>
                </div>
              </div>

              <ChatWindow
                messages={activeConversation?.messages ?? []}
                isTyping={isTyping}
                role={currentUser.role}
                onSourceSelect={setSelectedSource}
                onSuggestedQuery={handleSubmit}
                selectedSource={selectedSource}
                suggestedQueries={SUGGESTED_QUERIES[currentUser.role]}
                chatViewportRef={chatViewportRef}
              />

              <InputBox
                input={input}
                onInputChange={setInput}
                onSubmit={handleSubmit}
                isTyping={isTyping}
              />
            </section>

            <SourceViewer
              selectedSource={selectedSource}
              role={currentUser.role}
              documents={accessibleDocuments}
            />
          </main>
        )}
      </div>
    </div>
  )
}

export default App
