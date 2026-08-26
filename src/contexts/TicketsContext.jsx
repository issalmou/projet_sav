import { createContext, useState, useEffect } from 'react'

const TicketsContext = createContext(null)
const STORAGE_KEY = 'sav_tickets'

const newId = (tickets) => {
  const max = tickets.reduce((m, t) => {
    const n = parseInt(String(t.id).replace('TK-', ''), 10)
    return Number.isNaN(n) ? m : Math.max(m, n)
  }, 0)
  return 'TK-' + String(max + 1).padStart(3, '0')
}

const newMessage = (author, role, content) => ({
  id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
  author,
  role,
  content,
  createdAt: new Date().toISOString()
})

export function TicketsProvider({ children }) {
  const [tickets, setTickets] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY))
      return Array.isArray(stored) ? stored : []
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tickets))
  }, [tickets])

  const createTicket = (data, user = null) => {
    const now = new Date().toISOString()
    const ticket = {
      id: newId(tickets),
      title: data.title,
      description: data.description,
      status: 'open',
      priority: data.priority || 'medium',
      category: data.category || 'Autre',
      assignee: data.assignee || 'Non assigné',
      createdBy: user ? { email: user.email, name: user.name, role: user.role } : null,
      createdAt: now,
      updatedAt: now,
      attachments: [],
      messages: []
    }
    setTickets((prev) => [ticket, ...prev])
    return ticket
  }

  const getUserTickets = (user) => {
    if (!user) return tickets
    if (user.role === 'admin' || user.role === 'manager' || user.role === 'agent') {
      return tickets
    }
    return tickets.filter((t) => t.createdBy?.email === user.email)
  }

  const updateTicket = (id, data) =>
    setTickets((prev) =>
      prev.map((t) =>
        t.id === id ? { ...t, ...data, updatedAt: new Date().toISOString() } : t
      )
    )

  const deleteTicket = (id) =>
    setTickets((prev) => prev.filter((t) => t.id !== id))

  const addMessage = (id, { author, role, content }) =>
    setTickets((prev) =>
      prev.map((t) =>
        t.id === id
          ? {
              ...t,
              updatedAt: new Date().toISOString(),
              messages: [...t.messages, newMessage(author, role, content)]
            }
          : t
      )
    )

  return (
    <TicketsContext.Provider
      value={{
        tickets,
        getTicket: (id) => tickets.find((t) => t.id === id),
        createTicket,
        updateTicket,
        deleteTicket,
        addMessage,
        getUserTickets
      }}
    >
      {children}
    </TicketsContext.Provider>
  )
}

export default TicketsContext
