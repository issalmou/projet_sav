const backendUrl = (import.meta.env.VITE_API_URL || 'http://localhost:5000').replace(/\/$/, '')
export const API_URL = backendUrl.endsWith('/api/v1') ? backendUrl : `${backendUrl}/api/v1`

export async function loginRequest({ email, password }) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    let message = `Authentification impossible (${response.status})`
    try {
      const body = await response.json()
      if (body?.detail) message = body.detail
    } catch {
      // keep default message
    }
    throw new Error(message)
  }

  return response.json()
}

export async function getCurrentUserRequest(token) {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    let message = `Profil indisponible (${response.status})`
    try {
      const body = await response.json()
      if (body?.detail) message = body.detail
    } catch {
      // keep default message
    }
    throw new Error(message)
  }

  return response.json()
}
