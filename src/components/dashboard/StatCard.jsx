import { Ticket, MessageSquareMore, Timer ,Activity, Layers, Percent } from 'lucide-react'

const iconMap = {
  ticket: Ticket,
  message: MessageSquareMore,
  timer: Timer,
  activity: Activity,
  layers: Layers,
  percent: Percent,
}

const colorMap = {
  blue: { bg: 'bg-blue-50', text: 'text-blue-600', icon: 'text-blue-600' },
  teal: { bg: 'bg-teal-50', text: 'text-teal-600', icon: 'text-teal-600' },
  indigo: { bg: 'bg-indigo-50', text: 'text-indigo-600', icon: 'text-indigo-600' },
  orange: { bg: 'bg-orange-50', text: 'text-orange-600', icon: 'text-orange-600' },
}

function StatCard({ 
  title, 
  value, 
  subtitle, 
  trend, 
  icon = 'ticket', 
  color = 'blue' 
}) {
  const IconComponent = iconMap[icon] || Ticket
  const colors = colorMap[color] || colorMap.blue

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 custom-shadow card-hover transition-all">
      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-600">{title}</p>
          <h3 className="text-3xl font-bold text-slate-900">{value}</h3>
          {trend ? (
            <p className={`text-xs font-bold uppercase tracking-tight ${colors.text}`}>
              {trend}
            </p>
          ) : subtitle ? (
            <p className="text-xs text-slate-400">{subtitle}</p>
          ) : null}
        </div>
        <div className={`w-14 h-14 rounded-xl ${colors.bg} flex items-center justify-center ${colors.icon}`}>
          <IconComponent className="text-2xl" />
        </div>
      </div>
    </div>
  )
}

export default StatCard