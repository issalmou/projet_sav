import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { useAuth } from './contexts/useAuth'
import { TicketsProvider } from './contexts/TicketsContext'
import { AdminProvider } from './contexts/AdminContext'
import { can } from './contexts/roles'
import Login from './components/auth/Login'
import Signup from './components/auth/Signup'
import ForgotPassword from './components/auth/forgot-password'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import ChatBot from './pages/ChatBot'
import TicketsList from './pages/tickets/TicketsList'
import TicketDetail from './pages/tickets/TicketDetail'
import TicketCreate from './pages/tickets/TicketCreate'
import TicketEdit from './pages/tickets/TicketEdit'
import AdminLayout from './pages/admin/AdminLayout'
import AdminOverview from './pages/admin/AdminOverview'
import AdminUsers from './pages/admin/AdminUsers'
import UserForm from './pages/admin/UserForm'
import AdminDocuments from './pages/admin/AdminDocuments'
import DocumentForm from './pages/admin/DocumentForm'
import AdminIntegrations from './pages/admin/AdminIntegrations'
import AdminLogs from './pages/admin/AdminLogs'
import AdminSettings from './pages/admin/AdminSettings'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function PublicRoute({ children }) {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return children
}

function Guard({ permission, children }) {
  const { user } = useAuth()
  if (!can(user, permission)) {
    return <Navigate to={can(user, 'admin.view') ? '/admin' : '/dashboard'} replace />
  }
  return children
}

function AppRoutes() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><Signup /></PublicRoute>} />
      <Route path="/forgot-password" element={<PublicRoute><ForgotPassword /></PublicRoute>} />
      
      {/* Protected Routes with Layout */}
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/chat" element={<ChatBot />} />
        <Route path="/tickets" element={<TicketsList />} />
        <Route path="/tickets/new" element={<TicketCreate />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/tickets/:id/edit" element={<TicketEdit />} />
        <Route path="/products" element={<div className="p-8"><h1 className="text-2xl font-bold">Produits - Coming Soon</h1></div>} />
        <Route path="/knowledge" element={<div className="p-8"><h1 className="text-2xl font-bold">Knowledge Base - Coming Soon</h1></div>} />
        <Route path="/analytics" element={<div className="p-8"><h1 className="text-2xl font-bold">Analytiques - Coming Soon</h1></div>} />
        <Route path="/notifications" element={<div className="p-8"><h1 className="text-2xl font-bold">Notifications - Coming Soon</h1></div>} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      {/* Admin Routes */}
      <Route
        path="/admin"
        element={
          <Guard permission="admin.view">
            <AdminLayout />
          </Guard>
        }
      >
        <Route index element={<AdminOverview />} />
        <Route path="users" element={<Guard permission="users.manage"><AdminUsers /></Guard>} />
        <Route path="users/new" element={<Guard permission="users.manage"><UserForm /></Guard>} />
        <Route path="users/:id/edit" element={<Guard permission="users.manage"><UserForm /></Guard>} />
        <Route path="documents" element={<Guard permission="documents.manage"><AdminDocuments /></Guard>} />
        <Route path="documents/new" element={<Guard permission="documents.manage"><DocumentForm /></Guard>} />
        <Route path="documents/:id/edit" element={<Guard permission="documents.manage"><DocumentForm /></Guard>} />
        <Route path="integrations" element={<Guard permission="integrations.manage"><AdminIntegrations /></Guard>} />
        <Route path="logs" element={<Guard permission="logs.view"><AdminLogs /></Guard>} />
        <Route path="settings" element={<Guard permission="settings.manage"><AdminSettings /></Guard>} />
      </Route>

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AdminProvider>
          <TicketsProvider>
            <AppRoutes />
          </TicketsProvider>
        </AdminProvider>
      </AuthProvider>
    </Router>
  )
}

export default App
