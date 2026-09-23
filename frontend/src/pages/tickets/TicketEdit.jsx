import { useNavigate, useParams } from 'react-router-dom'
import TicketForm from './TicketForm'
import { useTickets } from '../../contexts/useTickets'
import { useAuth } from '../../contexts/useAuth'
import { useI18n } from '../../i18n/useI18n'

function TicketEdit({ basePath = '/tickets' }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getTicket, updateTicket } = useTickets()
  const { user } = useAuth()
  const { t } = useI18n()

  const ticket = getTicket(id)
  const source = ticket?.source || ticket?.creation_source || ticket?.origin
  const canAgentEdit = user?.role !== 'agent' || ['chatbot', 'responsable_sav'].includes(source)

  if (!ticket || !canAgentEdit) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-center">
        <div>
<h2 className="text-lg font-bold text-slate-900 mb-1">
              {!ticket ? t('td.notFound') : t('tf.editNotAllowed')}
            </h2>
          <button
             onClick={() => navigate(basePath)}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            {t('common.backToList')}
          </button>
        </div>
      </div>
    )
  }

  const handleSubmit = (values) => {
    updateTicket(ticket.id, values)
    navigate(`${basePath}/${ticket.id}`)
  }

  return (
    <TicketForm
      mode="edit"
      initialValues={ticket}
      onSubmit={handleSubmit}
      submitLabel={t('tf.submitEdit')}
      basePath={basePath}
    />
  )
}

export default TicketEdit
