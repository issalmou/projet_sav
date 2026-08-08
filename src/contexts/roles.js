export const ROLES = {
  admin: {
    label: 'Administrateur',
    color: 'bg-violet-50 text-violet-600 border-violet-100',
    dot: 'bg-violet-500',
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

export const ROLE_ORDER = ['admin', 'agent', 'client']

export const PERMISSIONS = {
  'admin.view': ['admin', 'agent'],
  'users.manage': ['admin'],
  'documents.manage': ['admin', 'agent'],
  'integrations.manage': ['admin'],
  'logs.view': ['admin', 'agent'],
  'settings.manage': ['admin'],
}

export function can(user, permission) {
  if (!user) return false
  const allowed = PERMISSIONS[permission]
  return Array.isArray(allowed) && allowed.includes(user.role)
}

export function isAdmin(user) {
  return user?.role === 'admin'
}
