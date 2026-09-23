import { useNavigate } from 'react-router-dom'
import TicketForm from '../tickets/TicketForm'
import { useTickets } from '../../contexts/useTickets'
import { useI18n } from '../../i18n/useI18n'

function AdminTicketCreate() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const { createTicket } = useTickets()

  const handleSubmit = async (values) => {
    const ticket = await createTicket(values)
    navigate(`/admin/tickets/${ticket.id}`)
  }

  return (
    <TicketForm
      mode="create"
      basePath="/admin/tickets"
      onSubmit={handleSubmit}
      submitLabel={t('tf.submitCreate')}
    />
  )
}

export default AdminTicketCreate