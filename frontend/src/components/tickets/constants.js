export const STATUSES = {
  open: { label: 'Ouvert', color: 'bg-blue-50 text-blue-700 border-blue-200', dot: 'bg-blue-500', icon: 'circle', step: 0 },
  in_progress: { label: 'En cours', color: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-500', icon: 'clock', step: 1 },
  escalated: { label: 'Escaladé', color: 'bg-red-50 text-red-700 border-red-200', dot: 'bg-red-500', icon: 'alert', step: 2 },
  resolved: { label: 'Résolu', color: 'bg-teal-50 text-teal-700 border-teal-200', dot: 'bg-teal-500', icon: 'check', step: 3 },
  closed: { label: 'Fermé', color: 'bg-slate-100 text-slate-600 border-slate-200', dot: 'bg-slate-400', icon: 'x', step: 4 }
}

export const STATUS_ORDER = ['open', 'in_progress', 'escalated', 'resolved', 'closed']

export const PRIORITIES = {
  high: { label: 'Haute', color: 'bg-red-50 text-red-700 border-red-200', dot: 'bg-red-500', rank: 2 },
  medium: { label: 'Moyenne', color: 'bg-orange-50 text-orange-700 border-orange-200', dot: 'bg-orange-500', rank: 1 },
  low: { label: 'Basse', color: 'bg-slate-50 text-slate-600 border-slate-200', dot: 'bg-slate-400', rank: 0 }
}

export const CATEGORIES = [
  { value: 'Matériel', label: 'Matériel', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  { value: 'Logiciel', label: 'Logiciel', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  { value: 'Réseau', label: 'Réseau', color: 'bg-purple-50 text-purple-700 border-purple-200' },
  { value: 'Facturation', label: 'Facturation', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  { value: 'Compte', label: 'Compte', color: 'bg-rose-50 text-rose-700 border-rose-200' },
  { value: 'Autre', label: 'Autre', color: 'bg-slate-50 text-slate-600 border-slate-200' }
]

export const categoryColor = (category) => {
  const found = CATEGORIES.find((c) => c.value === category)
  return found ? found.color : 'bg-slate-50 text-slate-600 border-slate-200'
}

export const STATUS_OPTIONS = STATUS_ORDER.map((value) => ({
  value,
  label: STATUSES[value].label
}))

export const PRIORITY_OPTIONS = [
  { value: 'high', label: 'Haute' },
  { value: 'medium', label: 'Moyenne' },
  { value: 'low', label: 'Basse' }
]

export const SORT_OPTIONS = [
  { value: 'newest', label: 'Plus récent' },
  { value: 'oldest', label: 'Plus ancien' },
  { value: 'priority', label: 'Priorité' },
  { value: 'status', label: 'Statut' },
  { value: 'title', label: 'Titre (A-Z)' }
]
