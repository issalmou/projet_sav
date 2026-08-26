// Données de démonstration utilisées uniquement lorsque l'API du backend
// n'est pas joignable (développement local sans serveur). Elles reproduisent
// le contrat de GET /api/dashboard/metrics et simulent de légères variations
// à chaque appel pour illustrer le rafraîchissement en temps réel.

const PRODUCTS = [
  { name: 'Monitor Pro 32" 4K OLED', weight: 5 },
  { name: 'Smart Gateway Hub X-1', weight: 4 },
  { name: 'Laptop Business 15"', weight: 3 },
  { name: 'Imprimante LaserJet Pro', weight: 2 },
  { name: 'Station de travail Graphite', weight: 2 },
  { name: 'Accessoires (clavier / souris)', weight: 1 },
]

const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min

const lastDays = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d
}

const shortDate = (d) =>
  d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })

const hourLabel = (i) => `${String(i).padStart(2, '0')}h`

// Détermine le découpage de la période sélectionnée.
function resolveRange(period, from, to) {
  if (period === 'day') return { type: 'hour', points: 24, days: 1 }
  if (period === 'month') return { type: 'day', points: 30, days: 30 }

  if (period === 'custom' && from && to) {
    const start = new Date(`${from}T00:00:00`)
    const end = new Date(`${to}T00:00:00`)
    const days = Math.max(1, Math.round((end - start) / 86400000) + 1)
    return { type: 'day', points: Math.min(days, 90), days }
  }

  return { type: 'day', points: 7, days: 7 }
}

// Génère un point de tendance (créé / résolu) pour un pas donné.
function trendPoint(index, range, dailyBase) {
  if (range.type === 'hour') {
    return { date: hourLabel(index), created: rand(0, 6), resolved: rand(0, 5) }
  }
  const day = lastDays(range.days - 1 - index)
  return { date: shortDate(day), created: rand(Math.max(1, dailyBase - 5), dailyBase), resolved: rand(Math.max(1, dailyBase - 6), dailyBase - 1) }
}

export function generateDemoMetrics({ period = 'week', from, to } = {}) {
  const range = resolveRange(period, from, to)

  const trend = Array.from({ length: range.points }, (_, i) => trendPoint(i, range, 18))

  const createdSum = trend.reduce((s, t) => s + t.created, 0)
  const total = Math.max(createdSum, range.points)

  const resolved = Math.round(total * (range.type === 'hour' ? 0.55 : 0.62))
  const closed = Math.round(total * (range.type === 'hour' ? 0.1 : 0.13))
  const inProgress = Math.round(total * (range.type === 'hour' ? 0.18 : 0.13))
  const open = total - resolved - closed - inProgress

  const rated = Math.max(5, Math.round(total * (range.type === 'hour' ? 0.5 : 0.6)))
  const satisfied = Math.round(rated * (0.78 + Math.random() * 0.1))
  const unsatisfied = Math.round(rated * (0.03 + Math.random() * 0.04))
  const neutral = Math.max(0, rated - satisfied - unsatisfied)

  const incidentsByProduct = PRODUCTS.map((p) => ({
    product: p.name,
    incidents: Math.max(
      1,
      Math.round((total * p.weight) / PRODUCTS.reduce((s, x) => s + x.weight, 0))
    ),
  }))

  return {
    generated_at: new Date().toISOString(),
    period,
    total_tickets: total,
    tickets_by_status: { open, in_progress: inProgress, resolved, closed },
    avg_resolution_hours: Number((17 + Math.random() * 6).toFixed(1)),
    csat: {
      score: Number((4.1 + Math.random() * 0.4).toFixed(1)),
      rated_count: rated,
      satisfied,
      neutral,
      unsatisfied,
    },
    incidents_by_product: incidentsByProduct,
    trend,
  }
}
