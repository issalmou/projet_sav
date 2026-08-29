import { useNavigate } from 'react-router-dom'
import TicketForm from '../tickets/TicketForm'
import { useTickets } from '../../contexts/useTickets'

function ResponsableSAVTicketCreate() {
  const navigate = useNavigate()
  const { createTicket } = useTickets()

  const handleSubmit = async (values) => {
    const ticket = await createTicket(values)
    navigate(`/responsable-sav/tickets/${ticket.id}`)
  }

  return (
    <TicketForm
      mode="create"
      onSubmit={handleSubmit}
      submitLabel="Créer le ticket"
    />
  )
}

export default ResponsableSAVTicketCreate
