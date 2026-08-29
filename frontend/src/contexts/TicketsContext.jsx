import { createContext, useCallback, useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useAuth } from './useAuth'

const TicketsContext = createContext(null)
const adapt = (ticket) => ({ ...ticket, createdAt: ticket.created_at, updatedAt: ticket.updated_at, createdBy: ticket.created_by, messages: ticket.messages || [] })

export function TicketsProvider({ children }) {
  const { user } = useAuth()
  const token = user?.access_token || user?.token
  const [tickets, setTickets] = useState([])
  const [error, setError] = useState(null)
  const reload = useCallback(async () => {
    try { setError(null); const data = await apiRequest('/tickets/', { token }); setTickets((Array.isArray(data) ? data : data.items || []).map(adapt)) }
    catch (err) { setError(err.message); setTickets([]) }
  }, [token])
  useEffect(() => { reload() }, [reload])
  const createTicket = async (data) => { const result = await apiRequest('/tickets/', { token, method: 'POST', body: JSON.stringify(data) }); await reload(); return adapt(result) }
  const updateTicket = async (id, data) => { const result = await apiRequest(`/tickets/${id}`, { token, method: 'PATCH', body: JSON.stringify(data) }); await reload(); return adapt(result) }
  const deleteTicket = async (id) => { await apiRequest(`/tickets/${id}`, { token, method: 'DELETE' }); await reload() }
  const addMessage = async (id, message) => { const result = await apiRequest(`/tickets/${id}/messages`, { token, method: 'POST', body: JSON.stringify(message) }); await reload(); return result }
  const getUserTickets = (currentUser) => currentUser?.role === 'admin' || currentUser?.role === 'manager' || currentUser?.role === 'agent' ? tickets : tickets.filter((t) => t.createdBy?.email === currentUser?.email)
  return <TicketsContext.Provider value={{ tickets, error, reload, getTicket: (id) => tickets.find((t) => t.id === id), createTicket, updateTicket, deleteTicket, addMessage, getUserTickets }}>{children}</TicketsContext.Provider>
}

export default TicketsContext
