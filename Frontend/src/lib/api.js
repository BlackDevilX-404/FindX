import { API_BASE_URL } from '../config/api'

export const AUTH_TOKEN_KEY = 'findx-auth-token'

function buildUrl(path) {
  return `${API_BASE_URL}${path}`
}

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    return response.json()
  }

  const text = await response.text()
  return text ? { detail: text } : null
}

async function apiRequest(path, options = {}) {
  const response = await fetch(buildUrl(path), options)
  const data = await parseResponse(response)

  if (!response.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : 'Request failed. Please try again.'
    throw new Error(detail)
  }

  return data
}

export function getStoredToken() {
  return window.localStorage.getItem(AUTH_TOKEN_KEY) ?? ''
}

export function storeToken(token) {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearStoredToken() {
  window.localStorage.removeItem(AUTH_TOKEN_KEY)
}

export function loginUser(email, password) {
  return apiRequest('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })
}

export function fetchCurrentUser(token) {
  return apiRequest('/api/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function sendChatMessage({ token, query, chatId, chatHistory }) {
  return apiRequest('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      query,
      chat_id: chatId,
      chat_history: chatHistory,
    }),
  })
}

export async function sendChatMessageStream({
  token,
  query,
  chatId,
  chatHistory,
  onEvent,
  signal,
}) {
  const response = await fetch(buildUrl('/api/chat/stream'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    signal,
    body: JSON.stringify({
      query,
      chat_id: chatId,
      chat_history: chatHistory,
    }),
  })

  if (!response.ok) {
    const data = await parseResponse(response)
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : 'Request failed. Please try again.'
    throw new Error(detail)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('Streaming is not supported by this browser or server response.')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let finalEvent = null

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) {
        continue
      }

      const event = JSON.parse(trimmed)
      onEvent?.(event)

      if (event.type === 'error') {
        throw new Error(event.detail || 'Streaming request failed.')
      }

      if (event.type === 'final') {
        finalEvent = event
      }
    }

    if (done) {
      break
    }
  }

  const trailing = buffer.trim()
  if (trailing) {
    const event = JSON.parse(trailing)
    onEvent?.(event)
    if (event.type === 'error') {
      throw new Error(event.detail || 'Streaming request failed.')
    }
    if (event.type === 'final') {
      finalEvent = event
    }
  }

  return finalEvent
}

export function uploadFileToSession({ token, sessionId, file, visibilityScope }) {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  formData.append('file', file)
  formData.append('visibility_scope', visibilityScope)

  return apiRequest('/api/upload/file', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })
}

export function updateDocumentVisibility({ token, documentId, visibilityScope }) {
  return apiRequest(`/api/documents/${documentId}/visibility`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      visibility_scope: visibilityScope,
    }),
  })
}

export function deleteDocument({ token, documentId }) {
  return apiRequest(`/api/documents/${documentId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}
