export const ROLES = {
  admin: {
    label: 'Administrateur',
    color: 'bg-violet-50 text-violet-600 border-violet-100',
    dot: 'bg-violet-500',
  },
  manager: {
    label: 'Responsable SAV',
    color: 'bg-amber-50 text-amber-600 border-amber-100',
    dot: 'bg-amber-500',
  },
  agent: {
    label: 'Agent Support',
    color: 'bg-blue-50 text-blue-600 border-blue-100',
    dot: 'bg-blue-500',
  },
  client: {
    label: 'Client',
    color: 'bg-teal-50 text-teal-600 border-teal-100',
    dot: 'bg-teal-500',
  },
}

export const ROLE_ORDER = ['admin', 'manager', 'agent', 'client']

// Correspondance entre les noms de rôles du backend (français) et les clés
// utilisées côté frontend.
export const BACKEND_ROLE_TO_KEY = {
  administrateur: 'admin',
  responsable_sav: 'manager',
  technicien: 'agent',
  client: 'client',
}

// Ramène un rôle (nom backend, clé frontend ou objet) vers une clé frontend.
export function resolveRole(role) {
  if (!role) return undefined
  const name = typeof role === 'object' ? role?.name : role
  if (!name) return undefined
  const key = String(name).toLowerCase()
  return BACKEND_ROLE_TO_KEY[key] || key
}

// Libellé lisible d'un rôle pour l'affichage.
export function roleLabel(role) {
  return ROLES[role]?.label || role
}

export const PERMISSIONS = {
  'admin.view': ['admin', 'agent'],
  'analytics.view': ['admin', 'manager', 'agent'],
  'users.manage': ['admin', 'manager'],
  'documents.manage': ['admin', 'manager', 'agent'],
  'integrations.manage': ['admin'],
  'logs.view': ['admin', 'manager', 'agent'],
  'settings.manage': ['admin'],
}

export const ROLE_HOME = {
  admin: '/admin',
  manager: '/responsable-sav',
  agent: '/agent',
  client: '/dashboard',
}

export function homeFor(user) {
  if (!user) return '/login'
  return ROLE_HOME[user.role] || '/dashboard'
}

export function can(user, permission) {
  if (!user) return false
  const allowed = PERMISSIONS[permission]
  return Array.isArray(allowed) && allowed.includes(user.role)
}

export function isAdmin(user) {
  return user?.role === 'admin'
}
