import { useNavigate } from 'react-router-dom'
import TicketForm from './TicketForm'
import { useTickets } from '../../contexts/useTickets'
import { useI18n } from '../../i18n/useI18n'

function TicketCreate() {
  const navigate = useNavigate()
  const { createTicket } = useTickets()
  const { t } = useI18n()

  const handleSubmit = async (values) => {
    const ticket = await createTicket(values)
    navigate(`/tickets/${ticket.id}`)
  }

  return (
    <TicketForm
      mode="create"
      onSubmit={handleSubmit}
      submitLabel={t('tf.submitCreate')}
    />
  )
}

export default TicketCreate
