import { useState, useRef, useEffect } from 'react'
import {
  Send,
  Plus,
  Search,
  Bot,
  User,
  MoreVertical,
  Paperclip,
  Smile,
  Mic,
  Sparkles,
  MessageSquare,
  Trash2,
  Clock,
  PanelLeftClose,
  PanelLeftOpen,
  Ticket
} from 'lucide-react'
import { useAuth } from '../contexts/useAuth'
import { useTickets } from '../contexts/useTickets'
import { apiRequest } from '../api/client'
import { useNavigate } from 'react-router-dom'

const quickSuggestions = [
  'Mon appareil ne démarre pas',
  'Comment mettre à jour le firmware ?',
  'Problème de connexion Wi-Fi',
  'Demander un agent humain'
]

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
            Créer un ticket
          </button>
        )}
        {!isUser && message.ticketCreated && (
          <button
            onClick={() => onNavigateToTicket(message.ticketId)}
            className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl transition-all active:scale-95"
          >
            <Ticket className="w-4 h-4" />
            Voir le ticket {message.ticketId}
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
  const [conversations, setConversations] = useState([])
  const [activeConversation, setActiveConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [pendingTicket, setPendingTicket] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
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
  }, [token])

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    const content = inputValue.trim()
    const newMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
    }

    setMessages(prev => [...prev, newMessage])
    setInputValue('')
    setIsTyping(true)
    try {
      const result = await apiRequest('/chat/message', { token, method: 'POST', body: JSON.stringify({ content, conversation_id: activeConversation || null }) })
      const message = result.message
      setActiveConversation(result.conversation_id)
      setMessages(prev => [...prev, { ...message, timestamp: new Date(message.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) }])
    } catch (error) {
      setMessages(prev => [...prev, { id: `error-${Date.now()}`, role: 'assistant', content: error.message }])
    } finally { setIsTyping(false) }
    inputRef.current?.focus()
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

  const handleCreateTicket = async () => {
    if (!pendingTicket) return
    
    const ticket = await createTicket({
      title: pendingTicket.title,
      description: pendingTicket.description,
      category: pendingTicket.category,
      priority: 'medium'
    }, user)

    const confirmMessage = {
      id: `ticket-${Date.now()}`,
      role: 'assistant',
      content: `✅ **Ticket ${ticket.id} créé avec succès !**\n\nVous pouvez suivre l'état de votre ticket en cliquant sur le bouton ci-dessous.`,
      timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
      ticketCreated: true,
      ticketId: ticket.id
    }

    setMessages(prev => [...prev, confirmMessage])
    setPendingTicket(null)
  }

  const handleNewConversation = () => {
    setActiveConversation(null)
    setMessages([])
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
            Nouvelle conversation
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Rechercher..."
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => setActiveConversation(conv.id)}
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
              <h2 className="text-sm font-bold text-slate-900">3LM solutions Ai Assistant</h2>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-teal-500 rounded-full" />
                <span className="text-[11px] text-teal-600 font-medium">En ligne</span>
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
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Bonjour, {user?.name?.split(' ')[0] || 'Utilisateur'} !</h2>
              <p className="text-slate-500 max-w-md mb-8">
                Je suis votre assistant 3LM Soltuion AI. Posez-moi des questions sur vos produits, services ou technique. Je suis là pour vous aider.
              </p>
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
              <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-lg transition-colors shrink-0">
                <Paperclip className="w-5 h-5" />
              </button>
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Envoyez un message à 3LM Soltuion AI..."
                rows={1}
                className="flex-1 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none resize-none max-h-32 min-h-[24px]"
                style={{ lineHeight: '1.5' }}
              />
              <div className="flex items-center gap-1 shrink-0">
                <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">
                  <Smile className="w-5 h-5" />
                </button>
                <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">
                  <Mic className="w-5 h-5" />
                </button>
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
              3LM Soltuion AI peut faire des erreurs. Vérifiez les informations importantes.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatBot
