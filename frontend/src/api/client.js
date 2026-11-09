import { store, signedOut } from '../app/store'

export const API = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin)).replace(/\/$/, '')

function messageForStatus(status, path) {
  if (status === 400) return 'Please check your information and try again.'
  if (status === 401) return 'The email or password is incorrect.'
  if (status === 403) return 'You don’t have access to do that. Contact support if you need help.'
  if (status === 404) return 'We couldn’t find what you’re looking for. It may have been removed.'
  if (status === 409) return 'That email address or username is already in use.'
  if (status === 413 && path.startsWith('/admin/knowledge/documents')) return 'That file is too large. Choose a file under 10 MB.'
  if (status === 415 && path.startsWith('/admin/knowledge/documents')) return 'Choose a PDF, TXT, or Markdown file.'
  if (status === 422 && path.startsWith('/admin/knowledge/documents')) return 'We could not read this document. Check that it contains readable text and try again.'
  if (status === 422) return 'Please check the information you entered and try again.'
  if (status === 429) return 'There have been too many attempts. Please wait a moment and try again.'
  if (status >= 500) return 'Something went wrong on our side. Please try again in a moment.'
  return 'We couldn’t complete that request. Please try again.'
}

export async function api(path, { token = store.getState().session.token, ...options } = {}) {
  const headers = new Headers(options.headers || {})
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response
  try {
    response = await fetch(`${API}${path}`, { ...options, headers })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('We couldn’t connect. Check your internet connection and try again.', { cause: error })
  }

  if (response.status === 401 && token) {
    sessionStorage.removeItem('support_token')
    store.dispatch(signedOut())
    throw new Error('Your session has expired. Please sign in again.')
  }
  if (!response.ok) throw new Error(messageForStatus(response.status, path))
  if (response.status === 204) return null

  try {
    return await response.json()
  } catch (error) {
    throw new Error('We received an unexpected response. Please try again.', { cause: error })
  }
}
