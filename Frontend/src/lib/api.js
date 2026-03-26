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
