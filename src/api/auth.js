export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

export async function loginRequest({ email, password }) {
  const response = await fetch(`${API_URL}/api/auth/login`, {
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
