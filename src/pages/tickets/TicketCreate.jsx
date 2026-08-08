import { useNavigate } from 'react-router-dom'
import TicketForm from './TicketForm'
import { useTickets } from '../../contexts/useTickets'

function TicketCreate() {
  const navigate = useNavigate()
  const { createTicket } = useTickets()

  const handleSubmit = (values) => {
    const ticket = createTicket(values)
    navigate(`/tickets/${ticket.id}`)
  }

  return (
    <TicketForm
      mode="create"
      onSubmit={handleSubmit}
      submitLabel="Créer le ticket"
    />
  )
}

export default TicketCreate
