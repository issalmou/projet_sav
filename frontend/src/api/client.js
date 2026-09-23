import { API_URL } from './auth'

export async function apiRequest(path, { token, ...options } = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    let message = `Requête impossible (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body?.detail)) {
        message = body.detail.map((item) => item?.msg || item?.detail).filter(Boolean).join(', ') || message
      }
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  if (response.status === 204) return null
  return response.json()
}
