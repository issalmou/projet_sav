import { useCallback, useEffect, useRef, useState } from 'react'
import { RefreshCw, Database, Clock, BarChart3, Smile, Package, TrendingUp, CalendarRange } from 'lucide-react'
import StatCard from '../../components/dashboard/StatCard'
import { useAuth } from '../../contexts/useAuth'
import { getMetricsRequest } from '../../api/analytics'
import { generateDemoMetrics } from '../../services/demoAnalytics'
import { StatusBarChart, SatisfactionChart, IncidentsChart, TrendChart } from '../../components/analytics/charts'

const REFRESH_INTERVAL_MS = 30000

const PERIODS = [
  { value: 'day', label: 'Jour' },
  { value: 'week', label: 'Semaine' },
  { value: 'month', label: 'Mois' },
  { value: 'custom', label: 'Personnalisé' },
]

const toISODate = (d) => d.toISOString().slice(0, 10)

const defaultCustomRange = () => {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 13)
  return { from: toISODate(from), to: toISODate(to) }
}

function formatFrDate(iso) {
  if (!iso) return '—'
  return new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR')
}

function formatHours(hours) {
  if (!Number.isFinite(hours)) return '—'
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  if (h === 0) return `${m} min`
  if (m === 0) return `${h} h`
  return `${h} h ${m} min`
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function ChartCard({ title, subtitle, icon: Icon, children, height = 'h-72' }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden custom-shadow">
      <div className="p-6 pb-0 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Icon className="w-4 h-4 text-slate-400" />
            {title}
          </h2>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className={`p-6 ${height}`}>
        {children}
      </div>
    </div>
  )
}

function Skeleton({ className }) {
  return <div className={`animate-pulse bg-slate-100 rounded-xl ${className}`} />
}

function Analytics() {
  const { user } = useAuth()
  const token = user?.access_token || user?.token || null

  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [live, setLive] = useState(false)
  const [period, setPeriod] = useState('week')
  const [customRange, setCustomRange] = useState(defaultCustomRange)
  const abortRef = useRef(null)

  const load = useCallback(async ({ background = false } = {}) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    if (background) setRefreshing(true)

    const query = { token, signal: controller.signal, period, from: customRange.from, to: customRange.to }

    try {
      const data = await getMetricsRequest(query)
      setMetrics(data)
      setLive(true)
    } catch (err) {
      if (err.name === 'AbortError') return
      // API injoignable (backend non démarré en local) : données de démonstration.
      setMetrics(generateDemoMetrics(query))
      setLive(false)
    } finally {
      setLoading(false)
      setRefreshing(false)
      setLastUpdated(new Date())
    }
  }, [token, period, customRange])

  useEffect(() => {
    const initial = setTimeout(() => load(), 0)

    const timer = setInterval(() => load({ background: true }), REFRESH_INTERVAL_MS)

    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') load({ background: true })
    }
    const refreshOnFocus = () => load({ background: true })

    window.addEventListener('focus', refreshOnFocus)
    document.addEventListener('visibilitychange', refreshWhenVisible)

    return () => {
      clearTimeout(initial)
      clearInterval(timer)
      window.removeEventListener('focus', refreshOnFocus)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
      abortRef.current?.abort()
    }
  }, [load])

  const stats = metrics
    ? {
        open: (metrics.tickets_by_status?.open ?? 0) + (metrics.tickets_by_status?.in_progress ?? 0),
        avgHours: formatHours(metrics.avg_resolution_hours),
        csat: `${Number(metrics.csat?.score ?? 0).toFixed(1)}/5`,
      }
    : null

  const periodLabel =
    period === 'day'
      ? "aujourd'hui"
      : period === 'week'
        ? 'cette semaine'
        : period === 'month'
          ? 'ce mois-ci'
          : `du ${formatFrDate(customRange.from)} au ${formatFrDate(customRange.to)}`

  const trendSubtitle =
    period === 'day'
      ? "Créés et résolus aujourd'hui, par heure"
      : period === 'month'
        ? 'Créés et résolus ces 30 derniers jours'
        : period === 'custom'
          ? `Du ${formatFrDate(customRange.from)} au ${formatFrDate(customRange.to)}`
          : 'Créés et résolus ces 7 derniers jours'

  const handleFromChange = (e) => {
    const from = e.target.value
    setCustomRange((prev) => ({ from, to: prev.to < from ? from : prev.to }))
  }

  const handleToChange = (e) => {
    const to = e.target.value
    setCustomRange((prev) => ({ to, from: prev.from > to ? to : prev.from }))
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* En-tête + indicateur temps réel */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tableau de bord Responsable SAV</h1>
            <p className="text-slate-500 mt-1">
              Performance du service : tickets, délais de résolution, satisfaction et incidents par produit.
            </p>
            <div className="flex items-center gap-3 mt-3">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide border ${
                  live
                    ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
                    : 'bg-amber-50 text-amber-600 border-amber-200'
                }`}
              >
                <span className="relative flex h-2 w-2">
                  <span
                    className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                      live ? 'bg-emerald-400' : 'bg-amber-400'
                    }`}
                  />
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${live ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                </span>
                {live ? 'Temps réel' : 'Mode démo'}
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                <Clock className="w-3.5 h-3.5" />
                Dernière mise à jour : {formatTime(lastUpdated)}
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                <Database className="w-3.5 h-3.5" />
                {live ? 'API connectée' : 'API indisponible'}
              </span>
            </div>
          </div>
          <button
            onClick={() => load()}
            disabled={refreshing}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
        </div>

        {/* Filtre de période */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            <CalendarRange className="w-4 h-4" />
            Période
          </div>
          <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                  period === p.value
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          {period === 'custom' && (
            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Du</label>
              <input
                type="date"
                value={customRange.from}
                max={customRange.to}
                onChange={handleFromChange}
                className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              />
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Au</label>
              <input
                type="date"
                value={customRange.to}
                min={customRange.from}
                max={toISODate(new Date())}
                onChange={handleToChange}
                className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              />
            </div>
          )}
        </div>

        {/* KPIs */}
        {loading && !metrics ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <Skeleton className="h-36" />
            <Skeleton className="h-36" />
            <Skeleton className="h-36" />
            <Skeleton className="h-36" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Total Tickets"
              value={metrics?.total_tickets ?? '—'}
              subtitle={`Période : ${periodLabel}`}
              icon="ticket"
              color="blue"
            />
            <StatCard
              title="Tickets en attente"
              value={stats?.open ?? '—'}
              subtitle="Ouverts + en cours"
              icon="layers"
              color="orange"
            />
            <StatCard
              title="Temps moyen de résolution"
              value={stats?.avgHours ?? '—'}
              subtitle="Depuis l'ouverture jusqu'à la résolution"
              icon="timer"
              color="indigo"
            />
            <StatCard
              title="Taux de satisfaction"
              value={stats?.csat ?? '—'}
              subtitle={`${metrics?.csat?.rated_count ?? 0} évaluations reçues`}
              icon="percent"
              color="teal"
            />
          </div>
        )}

        {/* Graphiques */}
        {metrics && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <ChartCard title="Tickets par statut" subtitle={`Répartition des tickets (${periodLabel})`} icon={BarChart3}>
                  <StatusBarChart data={metrics.tickets_by_status} />
                </ChartCard>
              </div>
              <ChartCard title="Satisfaction client" subtitle="Score global sur les tickets évalués" icon={Smile}>
                <SatisfactionChart csat={metrics.csat} />
              </ChartCard>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <ChartCard title="Évolution des tickets" subtitle={trendSubtitle} icon={TrendingUp}>
                  <TrendChart trend={metrics.trend} />
                </ChartCard>
              </div>
              <ChartCard title="Incidents par produit" subtitle={`Tickets ouverts par produit (${periodLabel})`} icon={Package}>
                <IncidentsChart products={metrics.incidents_by_product} />
              </ChartCard>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default Analytics
