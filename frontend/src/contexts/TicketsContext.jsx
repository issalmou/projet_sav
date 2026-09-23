import { createContext, useCallback, useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useAuth } from './useAuth'
import { PRIORITIES } from '../components/tickets/constants'
import { recordActivity } from '../services/activityLog'
import { canEditTicketAssignment } from '../components/tickets/permissions'

const TicketsContext = createContext(null)
const adapt = (ticket) => ({
  ...ticket,
  clientId: ticket.client_id || ticket.clientId,
  client: ticket.client || null,
  assigneeId: ticket.assigned_technician?.id || ticket.assigned_technician_id || ticket.assignee_id || ticket.assigneeId || null,
  assignedTechnicianId: ticket.assigned_technician?.id || ticket.assigned_technician_id || ticket.assignee_id || ticket.assigneeId || null,
  assignee: ticket.assigned_technician?.full_name || ticket.assigned_technician?.email || ticket.assignee || ticket.assignee_user?.full_name || ticket.assigned_technician_id || ticket.assignee_id || null,
  assignedTechnician: ticket.assigned_technician || null,
  priority: PRIORITIES[ticket.priority] ? ticket.priority : 'medium',
  createdAt: ticket.created_at || ticket.createdAt,
  updatedAt: ticket.updated_at || ticket.updatedAt,
  createdById: ticket.created_by_id || ticket.createdById,
  createdBy: ticket.created_by,
  conversationId: ticket.conversation_id || ticket.conversationId || null,
  source: ticket.conversation_id ? 'chatbot' : (ticket.source || ticket.creation_source || ticket.origin || null),
  createdVia: ticket.conversation_id ? 'chatbot' : 'manual',
})

export function TicketsProvider({ children }) {
  const { user } = useAuth()
  const token = user?.access_token || user?.token
  const [tickets, setTickets] = useState([])
  const [error, setError] = useState(null)
  const reload = useCallback(async () => {
    if (!token) return
    try { setError(null); const data = await apiRequest('/tickets/', { token }); setTickets((Array.isArray(data) ? data : data.items || []).map(adapt)) }
    catch (err) { setError(err.message); setTickets([]) }
  }, [token])
  useEffect(() => {
    if (!token) return undefined
    const timer = setTimeout(() => reload(), 0)
    return () => clearTimeout(timer)
  }, [token, reload])
  const payload = (data, includeStatus = false) => {
    const rest = { ...data }
    delete rest.status
    delete rest.priority
    delete rest.product
    delete rest.product_id
    return {
      ...rest,
      client_id: data.client_id || user?.id || null,
      assignee_id: data.assigned_technician_id || data.assignee_id || null,
      assigned_technician_id: data.assigned_technician_id || data.assignee_id || null,
      assignee: undefined,
      ...(includeStatus ? { status: data.status } : {})
    }
  }
  const updatePayload = (data) => {
    const next = {}
    const fields = ['status', 'title', 'description', 'category', 'client_id', 'source', 'escalationReason']
    fields.forEach((field) => {
      if (Object.prototype.hasOwnProperty.call(data, field)) next[field] = data[field]
    })

    const assignmentField = Object.prototype.hasOwnProperty.call(data, 'assigned_technician_id')
      ? data.assigned_technician_id
      : data.assignee_id
    if ((Object.prototype.hasOwnProperty.call(data, 'assigned_technician_id') || Object.prototype.hasOwnProperty.call(data, 'assignee_id')) && canEditTicketAssignment(user)) {
      next.assigned_technician_id = assignmentField
    }
    return next
  }
  const createTicket = async (data) => {
    let result = await apiRequest('/tickets/', { token, method: 'POST', body: JSON.stringify(payload(data)) })
    // Certains backends enregistrent l'assignation uniquement via la mise à jour.
    const technicianId = data.assigned_technician_id || data.assignee_id
    if (technicianId && result.id && String(result.assigned_technician_id || result.assignee_id || '') !== String(technicianId)) {
      result = await apiRequest(`/tickets/${result.id}`, {
        token,
        method: 'PATCH',
        body: JSON.stringify({ assignee_id: technicianId, assigned_technician_id: technicianId }),
      })
    }
    await reload()
    recordActivity({ actor: user?.name || user?.email, actorRole: user?.role, action: 'ticket.created', category: 'tickets', target: String(result.id), details: `Ticket créé : ${data.title || result.id}` })
    return adapt(result)
  }
  const updateTicket = async (id, data) => {
    const currentTicket = tickets.find((ticket) => String(ticket.id) === String(id))
    const result = await apiRequest(`/tickets/${id}`, {
      token,
      method: 'PATCH',
      body: JSON.stringify(updatePayload(data)),
    })
    const updatedTicket = adapt({ ...currentTicket, ...result })
    setTickets((current) => current.map((ticket) => (
      String(ticket.id) === String(id) ? updatedTicket : ticket
    )))
    recordActivity({ actor: user?.name || user?.email, actorRole: user?.role, action: 'ticket.updated', category: 'tickets', target: String(id), details: `Ticket modifié : ${id}` })
    return updatedTicket
  }
  const deleteTicket = async (id) => { await apiRequest(`/tickets/${id}`, { token, method: 'DELETE' }); await reload(); recordActivity({ actor: user?.name || user?.email, actorRole: user?.role, action: 'ticket.deleted', category: 'tickets', target: String(id), details: `Ticket supprimé : ${id}`, severity: 'warning' }) }
  const getUserTickets = (currentUser) => {
    const isStaff = ['admin', 'manager', 'agent'].includes(currentUser?.role)
    if (isStaff) return tickets

    return tickets.filter((ticket) => (
      (ticket.clientId && String(ticket.clientId) === String(currentUser?.id)) ||
      (ticket.createdById && String(ticket.createdById) === String(currentUser?.id)) ||
      ticket.client?.email === currentUser?.email ||
      ticket.createdBy?.email === currentUser?.email
    ))
  }
  return <TicketsContext.Provider value={{ tickets, error, reload, getTicket: (id) => tickets.find((t) => t.id === id), createTicket, updateTicket, deleteTicket, getUserTickets }}>{children}</TicketsContext.Provider>
}

export default TicketsContext
