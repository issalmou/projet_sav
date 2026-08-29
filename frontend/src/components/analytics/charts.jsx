import { Chart as ChartJS, ArcElement, BarElement, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler } from 'chart.js'
import { Bar, Doughnut, Line } from 'react-chartjs-2'

// Configuration globale de Chart.js (une seule fois au chargement du module).
ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler)

ChartJS.defaults.font.family = "'Inter', sans-serif"
ChartJS.defaults.font.size = 12
ChartJS.defaults.color = '#64748B'

const CHART_COLORS = {
  open: '#3B82F6',
  in_progress: '#F59E0B',
  resolved: '#14B8A6',
  closed: '#94A3B8',
}

const tooltipDefaults = {
  backgroundColor: '#0F172A',
  padding: 12,
  cornerRadius: 8,
  titleColor: '#E2E8F0',
  bodyColor: '#CBD5E1',
}

// Affiche une valeur au centre d'un graphique en anneau (taux de satisfaction).
const centerTextPlugin = {
  id: 'centerText',
  afterDraw(chart) {
    const meta = chart.getDatasetMeta(0)
    if (!meta?.data?.length) return
    const { ctx } = chart
    const { x, y } = meta.data[0]
    const value = chart.options.plugins?.centerText?.value
    ctx.save()
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.font = "700 22px 'Inter', sans-serif"
    ctx.fillStyle = '#0F172A'
    ctx.fillText(value, x, y)
    ctx.restore()
  },
}

export function StatusBarChart({ data }) {
  const labels = ['Ouvert', 'En cours', 'Résolu', 'Fermé']
  const chartData = {
    labels,
    datasets: [
      {
        label: 'Tickets',
        data: [data.open ?? 0, data.in_progress ?? 0, data.resolved ?? 0, data.closed ?? 0],
        backgroundColor: [CHART_COLORS.open, CHART_COLORS.in_progress, CHART_COLORS.resolved, CHART_COLORS.closed],
        borderRadius: 8,
        maxBarThickness: 48,
      },
    ],
  }

  return (
    <Bar
      data={chartData}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: tooltipDefaults,
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { weight: 600 } } },
          y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { precision: 0 } },
        },
      }}
    />
  )
}

export function SatisfactionChart({ csat }) {
  const total = (csat.satisfied || 0) + (csat.neutral || 0) + (csat.unsatisfied || 0)
  const chartData = {
    labels: ['Satisfaits', 'Neutres', 'Mécontents'],
    datasets: [
      {
        data: [csat.satisfied ?? 0, csat.neutral ?? 0, csat.unsatisfied ?? 0],
        backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
        borderWidth: 0,
        hoverOffset: 6,
      },
    ],
  }

  return (
    <Doughnut
      data={chartData}
      plugins={[centerTextPlugin]}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { usePointStyle: true, boxWidth: 8, padding: 16 },
          },
          tooltip: {
            ...tooltipDefaults,
            callbacks: {
              label: (ctx) => {
                const count = ctx.parsed ?? 0
                const pct = total > 0 ? Math.round((count / total) * 100) : 0
                return `${ctx.label} : ${count} (${pct}%)`
              },
            },
          },
          centerText: { value: `${Number(csat.score ?? 0).toFixed(1)}/5` },
        },
      }}
    />
  )
}

export function IncidentsChart({ products }) {
  const chartData = {
    labels: products.map((p) => p.product),
    datasets: [
      {
        label: 'Incidents',
        data: products.map((p) => p.incidents ?? 0),
        backgroundColor: '#3B82F6',
        borderRadius: 6,
        maxBarThickness: 22,
      },
    ],
  }

  return (
    <Bar
      data={chartData}
      options={{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: tooltipDefaults,
        },
        scales: {
          x: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { precision: 0 } },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      }}
    />
  )
}

export function TrendChart({ trend }) {
  const chartData = {
    labels: trend.map((t) => t.date),
    datasets: [
      {
        label: 'Créés',
        data: trend.map((t) => t.created ?? 0),
        borderColor: CHART_COLORS.open,
        backgroundColor: 'rgba(59, 130, 246, 0.08)',
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: CHART_COLORS.open,
      },
      {
        label: 'Résolus',
        data: trend.map((t) => t.resolved ?? 0),
        borderColor: CHART_COLORS.resolved,
        backgroundColor: 'rgba(20, 184, 166, 0.08)',
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: CHART_COLORS.resolved,
      },
    ],
  }

  return (
    <Line
      data={chartData}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { usePointStyle: true, boxWidth: 8, padding: 16 },
          },
          tooltip: tooltipDefaults,
        },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { precision: 0 } },
        },
      }}
    />
  )
}
