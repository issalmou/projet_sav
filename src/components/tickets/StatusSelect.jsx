import { STATUS_ORDER, STATUSES } from './constants'

export default function StatusSelect({ value, onChange }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {STATUS_ORDER.map((status) => {
        const s = STATUSES[status]
        const active = value === status
        return (
          <button
            key={status}
            type="button"
            onClick={() => onChange(status)}
            className={`flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-semibold border transition-all ${
              active
                ? `${s.color} ring-2 ring-offset-1 ${s.dot.replace('bg-', 'ring-')}`
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${s.dot}`} />
            {s.label}
          </button>
        )
      })}
    </div>
  )
}
