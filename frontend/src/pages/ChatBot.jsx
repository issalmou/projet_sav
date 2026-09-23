import { useState, useRef, useEffect } from 'react'
import {
  Send,
  Plus,
  Search,
  Bot,
  User,
  MoreVertical,
  Sparkles,
  MessageSquare,
  Trash2,
  Clock,
  PanelLeftClose,
  PanelLeftOpen,
  Ticket,
  ClipboardList
} from 'lucide-react'
import { useAuth } from '../contexts/useAuth'
import { useTickets } from '../contexts/useTickets'
import { apiRequest } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n/useI18n'

const isUuid = (value) => (
  typeof value === 'string'
  && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
)

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 mb-6">
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-md px-4 py-3 custom-shadow">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message, onCreateTicket, onNavigateToTicket }) {
  const { t } = useI18n()
  const isUser = message.role === 'user'

  return (
    <div className={`flex items-start gap-3 mb-6 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-slate-800' : 'bg-blue-600'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Bubble */}
      <div className={`max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-md'
            : 'bg-white border border-slate-200 text-slate-800 rounded-tl-md custom-shadow'
        }`}>
          <div className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</div>
        </div>
        <div className={`flex items-center gap-1.5 mt-1.5 ${isUser ? 'justify-end' : ''}`}>
          <Clock className="w-3 h-3 text-slate-400" />
          <span className="text-[10px] text-slate-400 font-medium">{message.timestamp}</span>
        </div>
        {!isUser && message.showCreateTicket && (
          <button
            onClick={onCreateTicket}
            className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-all active:scale-95"
          >
            <Ticket className="w-4 h-4" />
            {t('chat.createTicket')}
          </button>
        )}
        {!isUser && message.ticketCreated && (
          <button
            onClick={() => onNavigateToTicket(message.ticketId)}
            className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl transition-all active:scale-95"
          >
            <Ticket className="w-4 h-4" />
            {t('chat.viewTicket', { id: message.ticketId })}
          </button>
        )}
      </div>
    </div>
  )
}

function ChatBot() {
  const { user } = useAuth()
  const { createTicket } = useTickets()
  const navigate = useNavigate()
  const { t, language } = useI18n()
  const [conversations, setConversations] = useState([])
  const [activeConversation, setActiveConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [pendingTicket, setPendingTicket] = useState(null)
  const [productContext, setProductContext] = useState({
    description: '',
    installationDate: '',
    productId: '',
  })
  const [products, setProducts] = useState([])
  const [productsLoading, setProductsLoading] = useState(false)
  const [productsError, setProductsError] = useState('')
  const [productContextError, setProductContextError] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const conversationCreationRef = useRef(null)
  const conversationLoadRef = useRef(0)
  const conversationLoadingRef = useRef(false)
  const sendingRef = useRef(false)
  const token = user?.access_token || user?.token

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  useEffect(() => {
    if (!token) return
    apiRequest('/chat/conversations', { token }).then((data) => setConversations(data || [])).catch(() => setConversations([]))
  }, [token, user?.id, user?.role])

useEffect(() => {
    if (!token) return

    setProductsLoading(true)
    setProductsError('')
    const productsPath = user?.role === 'client' && user?.id
      ? `/clients/${user.id}/products`
      : '/products/'
    apiRequest(productsPath, { token })
      .then((data) => setProducts(Array.isArray(data) ? data : data.items || []))
      .catch((error) => {
        setProducts([])
        setProductsError(error.message || t('chat.loadError'))
      })
      .finally(() => setProductsLoading(false))
  }, [token, user?.id, user?.role, t])

  const ensureConversation = (title, productId) => {
    if (isUuid(activeConversation)) return Promise.resolve(activeConversation)
    if (conversationCreationRef.current) return conversationCreationRef.current

    conversationCreationRef.current = apiRequest('/chat/conversations', {
      token,
      method: 'POST',
      body: JSON.stringify({ title, product_id: productId }),
    })
      .then((conversation) => {
        const conversationId = conversation?.id || conversation?.conversation_id
if (!isUuid(conversationId)) {
          throw new Error(t('chat.contextInvalidUuid'))
        }

        setActiveConversation(conversationId)
        setConversations((previous) => [
          { ...conversation, id: conversationId, title: conversation.title || title },
          ...previous.filter((item) => item.id !== conversationId),
        ])
        return conversationId
      })
      .finally(() => {
        conversationCreationRef.current = null
      })

    return conversationCreationRef.current
  }

const handleSendMessage = async () => {
    if (!inputValue.trim() || sendingRef.current || conversationLoadingRef.current) return
    sendingRef.current = true

    const isFirstMessage = messages.length === 0
    if (isFirstMessage) {
      if (!productContext.description.trim() || !productContext.installationDate || !productContext.productId) {
        setProductContextError(t('chat.contextRequired'))
        sendingRef.current = false
        return
      }
    }

    const selectedProduct = products.find((product) => String(product.id) === String(productContext.productId))
    if (isFirstMessage && !isUuid(productContext.productId)) {
      setProductContextError(t('chat.contextInvalidUuid'))
      sendingRef.current = false
      return
    }
    const content = isFirstMessage
      ? `${inputValue.trim()}\n\nInformations produit :\n- Description : ${productContext.description.trim()}\n- Date d'installation : ${productContext.installationDate}\n- Produit : ${selectedProduct?.name || 'Produit sélectionné'}`
      : inputValue.trim()

    if (content.length > 8000) {
      setProductContextError(t('chat.tooLong'))
      sendingRef.current = false
      return
    }
    const newMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit' })
    }

    setMessages(prev => [...prev, newMessage])
    setInputValue('')
    setIsTyping(true)
    try {
      const conversationId = await ensureConversation(
        selectedProduct?.name || 'Nouvelle conversation',
        productContext.productId,
      )
      if (!isUuid(conversationId)) {
        throw new Error(t('chat.contextInvalidUuid'))
      }

      const payload = {
        content,
        conversation_id: conversationId,
        ...(isFirstMessage ? { product_id: productContext.productId } : {}),
      }
      const result = await apiRequest('/chat/message', { token, method: 'POST', body: JSON.stringify(payload) })
      const message = result.message
      if (isUuid(result.conversation_id)) {
        setActiveConversation(result.conversation_id)
      }
      setMessages(prev => [...prev, { ...message, timestamp: new Date(message.created_at).toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit' }) }])
    } catch (error) {
      setMessages(prev => [...prev, { id: `error-${Date.now()}`, role: 'assistant', content: error.message }])
    } finally {
      setIsTyping(false)
      sendingRef.current = false
    }
    inputRef.current?.focus()
  }

  const handleProductContextChange = (e) => {
    const { name, value } = e.target
    setProductContext((previous) => ({ ...previous, [name]: value }))
    if (productContextError) setProductContextError('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleSuggestionClick = (suggestion) => {
    setInputValue(suggestion)
    inputRef.current?.focus()
  }

  const handleConversationSelect = async (conversationId) => {
    if (!isUuid(conversationId)) return

    const requestId = conversationLoadRef.current + 1
    conversationLoadRef.current = requestId
    conversationLoadingRef.current = true
    setActiveConversation(conversationId)
    setMessages([])
    setIsTyping(false)

    try {
      const conversation = await apiRequest(`/chat/conversations/${conversationId}`, { token })
      if (conversationLoadRef.current !== requestId) return

setMessages((conversation.messages || []).map((message) => ({
        ...message,
        timestamp: new Date(message.created_at || message.createdAt).toLocaleTimeString(language, {
          hour: '2-digit',
          minute: '2-digit',
        }),
      })))
    } catch (error) {
      if (conversationLoadRef.current !== requestId) return
      setMessages([{
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: error.message || t('chat.historyError'),
      }])
    } finally {
      if (conversationLoadRef.current === requestId) conversationLoadingRef.current = false
    }
  }

  const handleCreateTicket = async () => {
    if (!pendingTicket) return
    
    const ticket = await createTicket({
      title: pendingTicket.title,
      description: pendingTicket.description,
      category: pendingTicket.category,
      priority: 'medium',
      source: 'chatbot',
    }, user)

    const confirmMessage = {
      id: `ticket-${Date.now()}`,
      role: 'assistant',
      content: t('chat.ticketCreated', { id: ticket.id }),
      timestamp: new Date().toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit' }),
      ticketCreated: true,
      ticketId: ticket.id
    }

    setMessages(prev => [...prev, confirmMessage])
    setPendingTicket(null)
  }

  const handleNewConversation = () => {
    conversationLoadRef.current += 1
    conversationLoadingRef.current = false
    setActiveConversation(null)
    setMessages([])
    setProductContext({ description: '', installationDate: '', productId: '' })
    setProductContextError('')
  }

  const handleDeleteConversation = (id, e) => {
    e.stopPropagation()
    apiRequest(`/chat/conversations/${id}`, { token, method: 'DELETE' }).catch(() => {})
    setConversations(prev => prev.filter(c => c.id !== id))
    if (activeConversation === id) {
      const remaining = conversations.filter(c => c.id !== id)
      if (remaining.length > 0) {
        setActiveConversation(remaining[0].id)
      } else {
        handleNewConversation()
      }
    }
  }

  const quickSuggestions = [t('chat.suggestion1'), t('chat.suggestion2'), t('chat.suggestion3'), t('chat.suggestion4')]

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-50 overflow-hidden">
      {/* Conversations Sidebar */}
      <div className={`${sidebarOpen ? 'w-72' : 'w-0'} transition-all duration-300 bg-white border-r border-slate-200 flex flex-col shrink-0 overflow-hidden`}>
        <div className="p-4 border-b border-slate-100">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-all active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            {t('chat.newConversation')}
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder={t('chat.search')}
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => handleConversationSelect(conv.id)}
              className={`group flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all ${
                conv.id === activeConversation
                  ? 'bg-blue-50 border border-blue-100'
                  : 'hover:bg-slate-50 border border-transparent'
              }`}
            >
              <MessageSquare className={`w-4 h-4 mt-0.5 shrink-0 ${
                conv.id === activeConversation ? 'text-blue-600' : 'text-slate-400'
              }`} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-semibold truncate ${
                  conv.id === activeConversation ? 'text-blue-900' : 'text-slate-800'
                }`}>
                  {conv.title}
                </p>
                {conv.lastMessage && (
                  <p className="text-xs text-slate-500 truncate mt-0.5">{conv.lastMessage}</p>
                )}
                <p className="text-[10px] text-slate-400 mt-1">{conv.timestamp}</p>
              </div>
              <button
                onClick={(e) => handleDeleteConversation(conv.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-500 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Header */}
        <div className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors"
            >
              {sidebarOpen ? (
                <PanelLeftClose className="w-5 h-5" />
              ) : (
                <PanelLeftOpen className="w-5 h-5" />
              )}
            </button>
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">{t('chat.title')}</h2>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-teal-500 rounded-full" />
                <span className="text-[11px] text-teal-600 font-medium">{t('chat.online')}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors">
              <MoreVertical className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            /* Empty State */
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-20 h-20 bg-blue-100 rounded-2xl flex items-center justify-center mb-6">
                <Sparkles className="w-10 h-10 text-blue-600" />
              </div>
<h2 className="text-2xl font-bold text-slate-900 mb-2">{t('chat.welcome', { name: user?.name?.split(' ')[0] || 'Utilisateur' })}</h2>
               <p className="text-slate-500 max-w-md mb-8">
                 {t('chat.intro')}
               </p>
               <div className="w-full max-w-2xl mb-6 rounded-2xl border border-blue-100 bg-white p-5 text-left shadow-sm">
                 <div className="flex items-start gap-3 mb-4">
                   <div className="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center shrink-0">
                     <ClipboardList className="w-5 h-5 text-blue-600" />
                   </div>
                   <div>
                     <h3 className="text-sm font-bold text-slate-900">{t('chat.productTitle')}</h3>
                     <p className="text-xs text-slate-500 mt-0.5">{t('chat.productSubtitle')}</p>
                   </div>
                 </div>
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                   <label className="block md:col-span-2">
                     <span className="block text-xs font-semibold text-slate-700 mb-1.5">{t('chat.productDesc')}</span>
                     <textarea
                       name="description"
                       value={productContext.description}
                       onChange={handleProductContextChange}
                       placeholder={t('chat.productDescPlaceholder')}
                       rows={3}
                       className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
                     />
                   </label>
                   <label className="block">
                     <span className="block text-xs font-semibold text-slate-700 mb-1.5">{t('chat.installDate')}</span>
                     <input
                       type="date"
                       name="installationDate"
                       value={productContext.installationDate}
                       onChange={handleProductContextChange}
                       className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                     />
                   </label>
                    <label className="block">
                      <span className="block text-xs font-semibold text-slate-700 mb-1.5">{t('chat.productBought')}</span>
                      {productsLoading ? (
                        <p className="text-sm text-slate-500 py-2.5">{t('chat.loadingProducts')}</p>
                      ) : products.length > 0 ? (
                        <select
                          name="productId"
                          value={productContext.productId}
                          onChange={handleProductContextChange}
                          className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                        >
                          <option value="">{t('chat.selectProduct')}</option>
                          {products.map((product) => (
                            <option key={product.id} value={product.id}>
                              {product.name}{product.reference ? ` (${product.reference})` : ''}
                            </option>
                          ))}
                        </select>
                      ) : null}
                      {productsError && <p className="mt-1.5 text-xs text-red-600">{productsError}</p>}
                      {!productsLoading && !productsError && products.length === 0 && (
                        <p className="mt-1.5 text-xs text-slate-500">{t('chat.noProducts')}</p>
                      )}
                    </label>
                 </div>
                 {productContextError && <p className="mt-3 text-xs font-medium text-red-600">{productContextError}</p>}
               </div>
               <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
                {quickSuggestions.map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="flex items-center gap-2 px-4 py-3 bg-white border border-slate-200 rounded-xl text-sm text-slate-700 font-medium hover:border-blue-300 hover:bg-blue-50 transition-all text-left"
                  >
                    <Sparkles className="w-4 h-4 text-blue-500 shrink-0" />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto">
              {messages.map((msg, i) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isLast={i === messages.length - 1}
                  onCreateTicket={handleCreateTicket}
                  onNavigateToTicket={(id) => navigate(`/tickets/${id}`)}
                />
              ))}
              {isTyping && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Suggestions (when messages exist) */}
        {messages.length > 0 && !isTyping && (
          <div className="px-6 pb-2">
            <div className="max-w-3xl mx-auto flex gap-2 overflow-x-auto scrollbar-hide pb-2">
              {quickSuggestions.map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs text-slate-600 font-medium hover:border-blue-300 hover:bg-blue-50 transition-all whitespace-nowrap shrink-0"
                >
                  <Sparkles className="w-3 h-3 text-blue-500" />
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="bg-white border-t border-slate-200 p-4 shrink-0">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-3 bg-slate-50 border border-slate-200 rounded-2xl p-3 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('chat.sendPlaceholder')}
                rows={1}
                className="flex-1 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none resize-none max-h-32 min-h-[24px]"
                style={{ lineHeight: '1.5' }}
              />
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim()}
                  className={`p-2.5 rounded-xl transition-all ${
                    inputValue.trim()
                      ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20 active:scale-95'
                      : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  }`}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
            <p className="text-center text-[10px] text-slate-400 mt-2">
              {t('chat.disclaimer')}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatBot
