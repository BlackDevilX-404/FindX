import { useEffect, useRef, useState } from 'react'
import AccessSidebar from './components/AccessSidebar'
import AdminDashboard from './components/AdminDashboard'
import ChatWindow from './components/ChatWindow'
import InputBox from './components/InputBox'
import {
  clearStoredToken,
  deleteDocument,
  fetchCurrentUser,
  getStoredToken,
  loginUser,
  sendChatMessageStream,
  storeToken,
  updateDocumentVisibility,
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
const LEFT_SIDEBAR_OPEN_KEY = 'findx-left-sidebar-open'
const RIGHT_SIDEBAR_OPEN_KEY = 'findx-right-sidebar-open'

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

function getDefaultSidebarOpen() {
  if (typeof window === 'undefined') {
    return true
  }

  return window.innerWidth >= 1280
}

function sortConversations(conversations) {
  return [...conversations].sort(
    (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
  )
}

function normalizeDocuments(documents) {
  return documents.map((document) => {
    const numericKeyFilename = Object.keys(document)
      .filter((key) => /^\d+$/.test(key))
      .sort((left, right) => Number(left) - Number(right))
      .map((key) => document[key])
      .join('')

    const filename =
      document.name ??
      document.document ??
      document.fileName ??
      document.title ??
      (numericKeyFilename || null) ??
      'Uploaded file'

    const normalizedDocument = {
      ...document,
      id: document.id ?? document.document_id ?? crypto.randomUUID(),
      name: filename,
      type: document.type ?? getFileTypeLabel(filename),
      ownerId: document.ownerId ?? document.uploaded_by ?? 'unknown-owner',
      ownerName:
        document.ownerName ??
        document.uploadedBy ??
        document.uploaded_by ??
        document.owner ??
        'Unknown owner',
      isSynced: document.isSynced ?? Boolean(document.document_id ?? document.id),
      summary:
        document.summary ??
        `Indexed ${document.chunks_indexed ?? 0} chunk(s) in ${document.category ?? 'GENERAL'} category.`,
    }

    if (document.visibilityScope) {
      return {
        ...normalizedDocument,
        visibilityScope: normalizeVisibilityScope(document.visibilityScope),
      }
    }

    if (Array.isArray(document.visibleTo)) {
      const hasHr = document.visibleTo.includes('hr-user')
      const hasDeveloper =
        document.visibleTo.includes('developer-user') ||
        document.visibleTo.includes('employee-user')
      const visibilityScope = hasHr && hasDeveloper ? 'both' : hasHr ? 'hr' : hasDeveloper ? 'developer' : 'private'
      const { visibleTo, ...rest } = document

      return {
        ...normalizedDocument,
        ...rest,
        visibilityScope,
      }
    }

    return {
      ...normalizedDocument,
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

function normalizeSource(source, index, scopeId = 'response') {
  const generatedId = [source?.doc_uuid, source?.doc, source?.document, source?.page ?? 'na', index]
    .filter(Boolean)
    .join(':')
  const baseId = (source?.id ?? generatedId) || `source-${index}`

  return {
    id: `${scopeId}:${baseId}`,
    doc:
      source?.doc ??
      source?.document ??
      source?.doc_uuid ??
      'Retrieved document',
    docUuid: source?.doc_uuid ?? null,
    page: source?.page ?? null,
    confidence: source?.confidence ?? 'Source-backed',
    text: source?.text ?? source?.snippet ?? '',
    mode: 'retrieval',
  }
}

function getFileTypeLabel(filename) {
  const extension = String(filename || '').split('.').pop()?.toUpperCase()
  return extension && extension !== String(filename || '').toUpperCase() ? extension : 'FILE'
}

function buildUploadedDocument(result, currentUser) {
  const filename = result?.document ?? 'Uploaded file'
  const ownerName =
    currentUser?.name ??
    currentUser?.username ??
    currentUser?.email ??
    'Unknown owner'

  return {
    id: result?.document_id ?? crypto.randomUUID(),
    name: filename,
    type: getFileTypeLabel(filename),
    ownerId: currentUser?.id ?? 'unknown-owner',
    ownerName,
    uploadedAt: 'Just now',
    visibilityScope: 'private',
    summary: `Indexed ${result?.chunks_indexed ?? 0} chunk(s) in ${result?.category ?? 'GENERAL'} category.`,
    category: result?.category ?? 'GENERAL',
    sensitivity: result?.sensitivity ?? null,
    isSynced: true,
  }
}

function getBackendSessionId(user) {
  return user?.id ?? ''
}

function getWorkspaceLayoutClass(isLeftSidebarOpen, isRightSidebarOpen) {
  if (isLeftSidebarOpen && isRightSidebarOpen) {
    return 'xl:grid-cols-[280px_minmax(0,1fr)_320px]'
  }

  if (isLeftSidebarOpen) {
    return 'xl:grid-cols-[280px_minmax(0,1fr)]'
  }

  if (isRightSidebarOpen) {
    return 'xl:grid-cols-[minmax(0,1fr)_320px]'
  }

  return 'xl:grid-cols-[minmax(0,1fr)]'
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
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(() =>
    readStorage(LEFT_SIDEBAR_OPEN_KEY, getDefaultSidebarOpen()),
  )
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(() =>
    readStorage(RIGHT_SIDEBAR_OPEN_KEY, getDefaultSidebarOpen()),
  )
  const chatViewportRef = useRef(null)
  const activeStreamControllerRef = useRef(null)
  const activeStreamConversationIdRef = useRef(null)

  const userKey = currentUser?.email.toLowerCase() ?? null
  const conversations = userKey ? chatStore[userKey] ?? [] : []
  const accessibleDocuments = currentUser ? getAccessibleDocuments(documents, currentUser) : []
  const activeConversation =
    currentUser && currentUser.role !== 'Admin'
      ? conversations.find((conversation) => conversation.id === activeConversationId) ??
        conversations[0] ??
        null
      : null
  const activeMessages = activeConversation?.messages ?? []
  const lastMessage = activeMessages[activeMessages.length - 1] ?? null
  const suggestedQueries = currentUser ? SUGGESTED_QUERIES[currentUser.role] ?? [] : []

  useEffect(() => {
    window.localStorage.setItem(DOCUMENTS_KEY, JSON.stringify(documents))
  }, [documents])

  useEffect(() => {
    window.localStorage.setItem(CHAT_STORE_KEY, JSON.stringify(chatStore))
  }, [chatStore])

  useEffect(() => {
    window.localStorage.setItem(
      LEFT_SIDEBAR_OPEN_KEY,
      JSON.stringify(isLeftSidebarOpen),
    )
  }, [isLeftSidebarOpen])

  useEffect(() => {
    window.localStorage.setItem(
      RIGHT_SIDEBAR_OPEN_KEY,
      JSON.stringify(isRightSidebarOpen),
    )
  }, [isRightSidebarOpen])

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
      behavior: lastMessage?.isStreaming ? 'auto' : 'smooth',
    })
  }, [
    activeMessages.length,
    activeConversationId,
    isTyping,
    lastMessage?.isStreaming,
    lastMessage?.text,
  ])

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

  const patchConversationMessage = (
    conversationId,
    messageId,
    updater,
    nextUpdatedAt = null,
  ) => {
    updateUserConversations((existing) =>
      existing.map((conversation) => {
        if (conversation.id !== conversationId) {
          return conversation
        }

        return {
          ...conversation,
          updatedAt: nextUpdatedAt ?? conversation.updatedAt,
          messages: conversation.messages.map((message) =>
            message.id === messageId ? updater(message) : message,
          ),
        }
      }),
    )
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
    activeStreamControllerRef.current?.abort()
    activeStreamControllerRef.current = null
    activeStreamConversationIdRef.current = null
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

  const handleDeleteConversation = (conversationId) => {
    if (!userKey || !currentUser || currentUser.role === 'Admin') {
      return
    }

    if (activeStreamConversationIdRef.current === conversationId) {
      activeStreamControllerRef.current?.abort()
      activeStreamControllerRef.current = null
      activeStreamConversationIdRef.current = null
      setIsTyping(false)
    }

    let nextActiveConversationId = null
    updateUserConversations((existing) => {
      const remaining = existing.filter((conversation) => conversation.id !== conversationId)
      nextActiveConversationId = remaining[0]?.id ?? null
      return remaining
    })

    if (activeConversationId === conversationId) {
      setActiveConversationId(nextActiveConversationId)
      setSelectedSource(null)
    }
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
    const assistantMessageId = crypto.randomUUID()
    const assistantCreatedAt = new Date().toISOString()
    updateUserConversations((existing) =>
      existing.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              updatedAt: assistantCreatedAt,
              messages: [
                ...conversation.messages,
                {
                  id: assistantMessageId,
                  type: 'assistant',
                  kind: 'response',
                  text: '',
                  explanation: 'Finding the strongest evidence...',
                  sources: [],
                  createdAt: assistantCreatedAt,
                  isStreaming: true,
                },
              ],
            }
          : conversation,
      ),
    )

    try {
      const streamController = new AbortController()
      activeStreamControllerRef.current = streamController
      activeStreamConversationIdRef.current = conversationId
      let streamedText = ''
      const finalResponse = await sendChatMessageStream({
        token: authToken,
        query,
        chatId: getBackendSessionId(currentUser),
        chatHistory: formatChatHistory(existingConversation?.messages ?? []),
        signal: streamController.signal,
        onEvent: (event) => {
          if (event.type === 'token') {
            streamedText += event.delta ?? ''
            patchConversationMessage(
              conversationId,
              assistantMessageId,
              (message) => ({
                ...message,
                text: streamedText,
              }),
            )
            return
          }

          if (event.type === 'final') {
            const sources = Array.isArray(event.sources)
              ? event.sources.map((source, index) => normalizeSource(source, index, assistantMessageId))
              : []

            patchConversationMessage(
              conversationId,
              assistantMessageId,
              (message) => ({
                ...message,
                text: event.answer || streamedText || message.text,
                explanation:
                  event.explanation ||
                  'This answer is grounded in the document evidence selected by the backend agent.',
                sources,
                isStreaming: false,
              }),
              new Date().toISOString(),
            )

            if (sources.length) {
              setSelectedSource(sources[0])
              setIsRightSidebarOpen(true)
            }
          }
        },
      })

      if (!finalResponse) {
        throw new Error('The backend stream ended before the final answer arrived.')
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        return
      }

      patchConversationMessage(
        conversationId,
        assistantMessageId,
        (message) => ({
          ...message,
          text: error.message || 'The backend could not answer this query.',
          explanation:
            'The request reached the server, but the backend agent could not complete retrieval or grounded generation.',
          sources: [],
          isStreaming: false,
        }),
        new Date().toISOString(),
      )
    } finally {
      if (activeStreamConversationIdRef.current === conversationId) {
        activeStreamControllerRef.current = null
        activeStreamConversationIdRef.current = null
      }
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
            visibilityScope: uploadVisibilityScope,
          }),
        ),
      )

      const nextDocuments = results
        .map((result) => buildUploadedDocument(result, currentUser))
        .filter(Boolean)
        .map((document) => ({
          ...document,
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

  const handleDocumentVisibilityChange = async (documentId, scope) => {
    if (!currentUser || !authToken) {
      return
    }

    const normalizedScope = normalizeVisibilityScope(scope)
    const targetDocument = documents.find((document) => document.id === documentId)

    if (!targetDocument || !canEditDocumentVisibility(targetDocument, currentUser)) {
      return
    }

    try {
      if (targetDocument.isSynced) {
        await updateDocumentVisibility({
          token: authToken,
          documentId,
          visibilityScope: normalizedScope,
        })
      }

      setDocuments((current) =>
        current.map((document) => {
          if (document.id !== documentId || !canEditDocumentVisibility(document, currentUser)) {
            return document
          }

          return {
            ...document,
            visibilityScope: normalizedScope,
          }
        }),
      )
      setUploadError('')
    } catch (error) {
      setUploadError(error.message || 'Visibility update failed.')
    }
  }

  const handleDeleteDocument = async (documentId) => {
    const target = documents.find((document) => document.id === documentId)

    if (!target || !canDeleteDocument(target, currentUser) || !authToken) {
      return
    }

    try {
      if (target.isSynced) {
        await deleteDocument({
          token: authToken,
          documentId,
        })
      }

      setDocuments((current) => current.filter((document) => document.id !== documentId))

      if (selectedSource?.doc === target.name) {
        setSelectedSource(null)
      }
      setUploadError('')
    } catch (error) {
      setUploadError(error.message || 'Delete failed.')
    }
  }

  if (isAuthLoading) {
    return (
      <div className="min-h-screen text-[var(--text-main)]">
        <div className="flex min-h-screen items-center justify-center px-4 text-sm text-[var(--text-muted)]">
          Restoring your workspace...
        </div>
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="min-h-screen text-[var(--text-main)]">
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
    <div className="min-h-screen text-[var(--text-main)] xl:h-screen xl:overflow-hidden">
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8 xl:h-screen xl:min-h-0">
        <Navbar
          currentUser={currentUser}
          onLogout={handleLogout}
          onNewChat={handleNewChat}
        />

        {uploadError ? (
          <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {uploadError}
          </div>
        ) : null}

        {isUploading ? (
          <div className="mt-4 rounded-2xl border border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3 text-sm text-[var(--text-muted)]">
            Uploading and indexing your files...
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
            className={`mt-4 grid flex-1 gap-4 xl:min-h-0 xl:overflow-hidden ${getWorkspaceLayoutClass(
              isLeftSidebarOpen,
              isRightSidebarOpen,
            )}`}
          >
            {isLeftSidebarOpen ? (
              <AccessSidebar
                currentUser={currentUser}
                documents={accessibleDocuments}
                conversations={conversations}
                activeConversationId={activeConversation?.id}
                onConversationSelect={setActiveConversationId}
                onDeleteConversation={handleDeleteConversation}
                onNewChat={handleNewChat}
                uploadVisibilityScope={uploadVisibilityScope}
                onUploadVisibilityChange={handleUploadVisibilityChange}
                onFileUpload={handleFileUpload}
                onToggle={() => setIsLeftSidebarOpen(false)}
              />
            ) : null}

            <section className="flex min-h-[72vh] flex-col rounded-3xl border border-[var(--border-soft)] bg-[var(--surface-1)] shadow-[0_24px_60px_rgba(0,0,0,0.16)] xl:min-h-0 xl:overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-soft)] px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsLeftSidebarOpen((current) => !current)}
                    className="rounded-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--text-main)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]"
                  >
                    {isLeftSidebarOpen ? 'Hide history' : 'Show history'}
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsRightSidebarOpen((current) => !current)}
                    className="rounded-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--text-main)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]"
                  >
                    {isRightSidebarOpen ? 'Hide evidence' : 'Show evidence'}
                  </button>
                </div>

                <div className="text-right">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Current thread</p>
                  <p className="mt-1 text-sm text-[var(--text-main)]">{activeConversation?.title ?? 'New chat'}</p>
                </div>
              </div>

              <ChatWindow
                messages={activeConversation?.messages ?? []}
                isTyping={isTyping}
                onSourceSelect={(source) => {
                  setSelectedSource(source)
                  setIsRightSidebarOpen(true)
                }}
                onSuggestedQuery={handleSubmit}
                selectedSource={selectedSource}
                suggestedQueries={suggestedQueries}
                chatViewportRef={chatViewportRef}
              />

              <InputBox
                input={input}
                onInputChange={setInput}
                onSubmit={handleSubmit}
                isTyping={isTyping}
              />
            </section>

            {isRightSidebarOpen ? (
              <SourceViewer
                selectedSource={selectedSource}
                onToggle={() => setIsRightSidebarOpen(false)}
              />
            ) : null}
          </main>
        )}
      </div>
    </div>
  )
}

export default App
