const STATUS_KEYS = ['open', 'in_progress', 'resolved', 'closed']

function asDate(value) {
  const date = value ? new Date(value) : null
  return date && !Number.isNaN(date.getTime()) ? date : null
}

function periodBounds(period, from, to) {
  const end = period === 'custom' && to ? new Date(`${to}T23:59:59`) : new Date()
  const days = period === 'day' ? 1 : period === 'month' ? 30 : 7
  const start = period === 'custom' && from ? new Date(`${from}T00:00:00`) : new Date(end)
  if (!(period === 'custom' && from)) start.setDate(end.getDate() - days + 1)
  return { start, end }
}

function inPeriod(ticket, start, end) {
  const created = asDate(ticket.createdAt || ticket.created_at)
  return created ? created >= start && created <= end : true
}

function trendFor(tickets, period, from, to) {
  const { start, end } = periodBounds(period, from, to)
  const count = period === 'day' ? 24 : Math.min(90, Math.max(1, Math.ceil((end - start) / 86400000)))
  return Array.from({ length: count }, (_, index) => {
    const bucketStart = new Date(start)
    if (period === 'day') bucketStart.setHours(index, 0, 0, 0)
    else bucketStart.setDate(start.getDate() + index)
    const bucketEnd = new Date(bucketStart)
    if (period === 'day') bucketEnd.setHours(bucketStart.getHours() + 1)
    else bucketEnd.setDate(bucketStart.getDate() + 1)
    const matching = tickets.filter((ticket) => {
      const created = asDate(ticket.createdAt || ticket.created_at)
      return created && created >= bucketStart && created < bucketEnd
    })
    return {
      date: period === 'day'
        ? `${String(index).padStart(2, '0')}h`
        : bucketStart.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }),
      created: matching.length,
      resolved: matching.filter((ticket) => ['resolved', 'closed'].includes(ticket.status)).length,
    }
  })
}

export function buildAnalyticsMetrics({ tickets = [], products = [], period = 'week', from, to }) {
  const { start, end } = periodBounds(period, from, to)
  const filtered = tickets.filter((ticket) => inPeriod(ticket, start, end))
  const ticketsByStatus = Object.fromEntries(STATUS_KEYS.map((status) => [
    status,
    filtered.filter((ticket) => ticket.status === status).length,
  ]))
  const productNames = new Map(products.map((product) => [String(product.id), product.name]))
  const incidents = new Map()

  filtered.forEach((ticket) => {
    const productId = ticket.product_id || ticket.productId || ticket.product?.id
    const name = ticket.product?.name || productNames.get(String(productId)) || 'Produit non précisé'
    incidents.set(name, (incidents.get(name) || 0) + 1)
  })

  const resolutionHours = filtered.flatMap((ticket) => {
    if (!['resolved', 'closed'].includes(ticket.status)) return []
    const created = asDate(ticket.createdAt || ticket.created_at)
    const resolved = asDate(ticket.resolved_at || ticket.resolvedAt || ticket.closed_at || ticket.updatedAt || ticket.updated_at)
    return created && resolved && resolved >= created ? [(resolved - created) / 3600000] : []
  })
  const ratings = filtered.map((ticket) => Number(ticket.satisfaction_score ?? ticket.rating ?? ticket.csat)).filter(Number.isFinite)
  const score = ratings.length ? ratings.reduce((sum, rating) => sum + rating, 0) / ratings.length : 0

  return {
    generated_at: new Date().toISOString(),
    total_tickets: filtered.length,
    tickets_by_status: ticketsByStatus,
    avg_resolution_hours: resolutionHours.length
      ? resolutionHours.reduce((sum, hours) => sum + hours, 0) / resolutionHours.length
      : 0,
    csat: {
      score,
      rated_count: ratings.length,
      satisfied: ratings.filter((rating) => rating >= 4).length,
      neutral: ratings.filter((rating) => rating === 3).length,
      unsatisfied: ratings.filter((rating) => rating < 3).length,
    },
    incidents_by_product: [...incidents.entries()].map(([product, count]) => ({ product, incidents: count })),
    trend: trendFor(filtered, period, from, to),
  }
}
