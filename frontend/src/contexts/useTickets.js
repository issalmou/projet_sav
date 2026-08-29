import { useContext } from 'react'
import TicketsContext from './TicketsContext'

export function useTickets() {
  const context = useContext(TicketsContext)
  if (!context) {
    throw new Error('useTickets must be used within a TicketsProvider')
  }
  return context
}
