const STAFF_ROLES = new Set(['admin', 'manager', 'superuser'])

export function isStaffOrSuperuser(user) {
  return Boolean(
    user && (
      STAFF_ROLES.has(user.role) ||
      user.is_superuser === true ||
      user.isSuperuser === true
    )
  )
}

export function getAssignedTechnicianId(ticket) {
  return ticket?.assigned_technician?.id ||
    ticket?.assignedTechnician?.id ||
    ticket?.assigned_technician_id ||
    ticket?.assignedTechnicianId ||
    ticket?.assigneeId ||
    ticket?.assignee_id ||
    null
}

export function canEditTicketStatus(ticket, currentUser) {
  if (!ticket || !currentUser || currentUser.role === 'client') return false
  if (isStaffOrSuperuser(currentUser)) return true

  const isTechnician = currentUser.role === 'agent' || currentUser.role === 'technicien'
  return isTechnician && String(getAssignedTechnicianId(ticket)) === String(currentUser.id)
}

export function canEditTicketAssignment(currentUser) {
  return isStaffOrSuperuser(currentUser)
}
