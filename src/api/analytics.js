import { API_URL } from './auth'

// Endpoint d'agrégation des indicateurs du tableau de bord SAV.
// Contrat attendu (à fournir par GET /api/dashboard/metrics) :
// {
//   generated_at: string (ISO),
//   total_tickets: number,
//   tickets_by_status: { open, in_progress, resolved, closed },
//   avg_resolution_hours: number,
//   csat: { score, rated_count, satisfied, neutral, unsatisfied },
//   incidents_by_product: [{ product, incidents }],
//   trend: [{ date, created, resolved }]
// }
// Paramètres de filtre : period (day|week|month|custom), from/to (YYYY-MM-DD) pour custom.
export async function getMetricsRequest({ token, signal, period = 'week', from, to }) {
  const params = new URLSearchParams()
  params.set('period', period)
  if (period === 'custom') {
    if (from) params.set('from', from)
    if (to) params.set('to', to)
  }

  const response = await fetch(`${API_URL}/api/dashboard/metrics?${params.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    signal,
  })

  if (!response.ok) {
    let message = `Métriques indisponibles (${response.status})`
    try {
      const body = await response.json()
      if (body?.detail) message = body.detail
    } catch {
      // garde le message par défaut
    }
    throw new Error(message)
  }

  return response.json()
}
