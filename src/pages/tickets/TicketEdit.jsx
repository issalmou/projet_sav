import { useNavigate, useParams } from 'react-router-dom'
import TicketForm from './TicketForm'
import { useTickets } from '../../contexts/useTickets'

function TicketEdit() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getTicket, updateTicket } = useTickets()

  const ticket = getTicket(id)

  if (!ticket) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-center">
        <div>
          <h2 className="text-lg font-bold text-slate-900 mb-1">Ticket introuvable</h2>
          <button
            onClick={() => navigate('/tickets')}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            Retour à la liste
          </button>
        </div>
      </div>
    )
  }

  const handleSubmit = (values) => {
    updateTicket(ticket.id, values)
    navigate(`/tickets/${ticket.id}`)
  }

  return (
    <TicketForm
      mode="edit"
      initialValues={ticket}
      onSubmit={handleSubmit}
      submitLabel="Enregistrer les modifications"
    />
  )
}

export default TicketEdit
