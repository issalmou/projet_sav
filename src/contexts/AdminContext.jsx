import { createContext, useState, useEffect, useCallback } from 'react'
import { useAuth } from './useAuth'

const AdminContext = createContext(null)

const USERS_KEY = 'sav_admin_users'
const DOCUMENTS_KEY = 'sav_admin_documents'
const INTEGRATIONS_KEY = 'sav_admin_integrations'
const SETTINGS_KEY = 'sav_admin_settings'
const LOGS_KEY = 'sav_admin_logs'

function load(key, fallback) {
  try {
    const stored = JSON.parse(localStorage.getItem(key))
    return stored ?? fallback
  } catch {
    return fallback
  }
}

const genId = (prefix) =>
  prefix +
  '-' +
  Date.now().toString(36).toUpperCase().slice(-6) +
  Math.random().toString(36).slice(2, 4).toUpperCase()

const nextId = (list, prefix) => {
  const max = list.reduce((m, item) => {
    const n = parseInt(String(item.id).replace(prefix + '-', ''), 10)
    return Number.isNaN(n) ? m : Math.max(m, n)
  }, 0)
  return `${prefix}-${String(max + 1).padStart(3, '0')}`
}

const daysAgo = (days, hours = 0) => {
  const d = new Date()
  d.setDate(d.getDate() - days)
  d.setHours(d.getHours() - hours)
  return d.toISOString()
}

const SEED_USERS = [
  {
    id: 'USR-001',
    name: 'Marie Dupont',
    email: 'marie@3lmsolutions.com',
    role: 'admin',
    status: 'active',
    department: 'Direction Support',
    phone: '+33 6 12 34 56 78',
    lastLogin: daysAgo(0, 1),
    createdAt: daysAgo(120),
  },
  {
    id: 'USR-002',
    name: 'Karim Benali',
    email: 'karim@3lmsolutions.com',
    role: 'agent',
    status: 'active',
    department: 'Support Niveau 1',
    phone: '+33 6 23 45 67 89',
    lastLogin: daysAgo(0, 3),
    createdAt: daysAgo(95),
  },
  {
    id: 'USR-003',
    name: 'Sophie Martin',
    email: 'sophie@3lmsolutions.com',
    role: 'agent',
    status: 'active',
    department: 'Support Niveau 2',
    phone: '+33 6 34 56 78 90',
    lastLogin: daysAgo(1),
    createdAt: daysAgo(60),
  },
  {
    id: 'USR-004',
    name: 'Lucas Bernard',
    email: 'lucas@client-example.com',
    role: 'client',
    status: 'active',
    department: '3LM Solutions',
    phone: '+33 6 45 67 89 01',
    lastLogin: daysAgo(2),
    createdAt: daysAgo(45),
  },
  {
    id: 'USR-005',
    name: 'Emma Rousseau',
    email: 'emma@client-example.com',
    role: 'client',
    status: 'inactive',
    department: 'GreenTech SAS',
    phone: '+33 6 56 78 90 12',
    lastLogin: daysAgo(30),
    createdAt: daysAgo(20),
  },
]

const SEED_DOCUMENTS = [
  {
    id: 'DOC-001',
    title: 'Comment configurer le Smart Gateway Hub X-1 ?',
    type: 'faq',
    category: 'Configuration',
    language: 'fr',
    status: 'published',
    content:
      "Branchez le hub sur votre réseau local puis ouvrez l'application. Suivez l'assistant de configuration pour associer vos équipements. Le hub est prêt en moins de 5 minutes.",
    views: 342,
    tags: ['hub', 'configuration', 'premiers pas'],
    updatedAt: daysAgo(3),
    createdAt: daysAgo(60),
  },
  {
    id: 'DOC-002',
    title: "Manuel d'installation - Monitor Pro 32\"",
    type: 'manual',
    category: 'Manuels',
    language: 'fr',
    status: 'published',
    content:
      "Ce manuel décrit l'installation du Monitor Pro 32\" : déballage, montage du support, branchement des câbles et activation de la garantie via le portail.",
    views: 521,
    tags: ['installation', 'monitor', 'manuel'],
    updatedAt: daysAgo(10),
    createdAt: daysAgo(90),
  },
  {
    id: 'DOC-003',
    title: "Que faire en cas d'écran noir ?",
    type: 'faq',
    category: 'Dépannage',
    language: 'fr',
    status: 'published',
    content:
      "Vérifiez le câble d'alimentation, le câble vidéo puis redémarrez l'appareil. Si le problème persiste, réinitialisez le moniteur via le menu OSD (appui long sur le bouton central).",
    views: 198,
    tags: ['dépannage', 'écran', 'monitor'],
    updatedAt: daysAgo(5),
    createdAt: daysAgo(50),
  },
  {
    id: 'DOC-004',
    title: "Guide de l'IA conversationnelle 3LM",
    type: 'guide',
    category: 'Guides',
    language: 'fr',
    status: 'draft',
    content:
      "Guide complet sur les capacités de l'IA : création d'agents, réponses automatisées, escalade vers un agent humain et bonnes pratiques.",
    views: 0,
    tags: ['ia', 'guide', 'agents'],
    updatedAt: daysAgo(1),
    createdAt: daysAgo(4),
  },
  {
    id: 'DOC-005',
    title: "Manuel utilisateur - Application mobile",
    type: 'manual',
    category: 'Manuels',
    language: 'fr',
    status: 'published',
    content:
      "Toutes les fonctionnalités de l'application mobile 3LM Solutions : création de tickets, messagerie, suivi des produits et notifications push.",
    views: 87,
    tags: ['mobile', 'application', 'manuel'],
    updatedAt: daysAgo(7),
    createdAt: daysAgo(15),
  },
]

const SEED_INTEGRATIONS = [
  {
    id: 'INT-001',
    provider: 'salesforce',
    name: 'Salesforce CRM',
    type: 'crm',
    enabled: true,
    status: 'connected',
    apiUrl: 'https://mycompany.salesforce.com/services/data/v58.0',
    apiKey: 'sk-live-••••••••••••',
    syncDirection: 'bidirectional',
    syncFrequency: 'realtime',
    lastSync: daysAgo(0, 2),
  },
  {
    id: 'INT-002',
    provider: 'sap',
    name: 'SAP Business One',
    type: 'erp',
    enabled: true,
    status: 'connected',
    apiUrl: 'https://erp.3lmsolutions.com:50000/b1s/v2',
    apiKey: 'b1-••••••••••••••',
    syncDirection: 'oneway_in',
    syncFrequency: 'hourly',
    lastSync: daysAgo(0, 1),
  },
  {
    id: 'INT-003',
    provider: 'hubspot',
    name: 'HubSpot CRM',
    type: 'crm',
    enabled: false,
    status: 'disconnected',
    apiUrl: 'https://api.hubapi.com',
    apiKey: '',
    syncDirection: 'oneway_out',
    syncFrequency: 'daily',
    lastSync: null,
  },
]

const SEED_SETTINGS = {
  companyName: '3LM Solutions',
  supportEmail: 'support@3lmsolutions.com',
  supportPhone: '+33 1 23 45 67 89',
  language: 'fr',
  timezone: 'Europe/Paris',
  defaultTicketPriority: 'medium',
  slaDays: 5,
  autoResponder: true,
  aiEnabled: true,
  maintenanceMode: false,
  emailNotifications: {
    ticketCreated: true,
    ticketAssigned: true,
    ticketResolved: true,
    weeklyDigest: false,
  },
  security: {
    twoFactorAuth: false,
    sessionTimeout: 30,
    passwordPolicy: 'medium',
  },
}

const SEED_LOGS = [
  {
    id: 'LOG-001',
    action: 'auth.login',
    category: 'auth',
    actor: 'Marie Dupont',
    actorRole: 'admin',
    target: 'USR-001',
    details: "Connexion réussie depuis l'interface d'administration",
    severity: 'info',
    ip: '192.168.1.24',
    createdAt: daysAgo(0, 1),
  },
  {
    id: 'LOG-002',
    action: 'document.publish',
    category: 'documents',
    actor: 'Karim Benali',
    actorRole: 'agent',
    target: 'DOC-005',
    details: "Publication du manuel utilisateur - Application mobile",
    severity: 'info',
    ip: '192.168.1.42',
    createdAt: daysAgo(1),
  },
  {
    id: 'LOG-003',
    action: 'integration.update',
    category: 'integrations',
    actor: 'Marie Dupont',
    actorRole: 'admin',
    target: 'INT-002',
    details: 'Fréquence de synchronisation SAP modifiée vers horaire',
    severity: 'warning',
    ip: '192.168.1.24',
    createdAt: daysAgo(1, 4),
  },
  {
    id: 'LOG-004',
    action: 'settings.update',
    category: 'settings',
    actor: 'Marie Dupont',
    actorRole: 'admin',
    target: 'SETTINGS',
    details: 'Activation du mode maintenance',
    severity: 'critical',
    ip: '192.168.1.24',
    createdAt: daysAgo(2),
  },
  {
    id: 'LOG-005',
    action: 'user.create',
    category: 'users',
    actor: 'Sophie Martin',
    actorRole: 'agent',
    target: 'USR-005',
    details: "Création du compte Emma Rousseau",
    severity: 'info',
    ip: '192.168.1.57',
    createdAt: daysAgo(2, 6),
  },
]

export function AdminProvider({ children }) {
  const { user } = useAuth()

  const [users, setUsers] = useState(() => load(USERS_KEY, SEED_USERS))
  const [documents, setDocuments] = useState(() => load(DOCUMENTS_KEY, SEED_DOCUMENTS))
  const [integrations, setIntegrations] = useState(() => load(INTEGRATIONS_KEY, SEED_INTEGRATIONS))
  const [settings, setSettings] = useState(() => load(SETTINGS_KEY, SEED_SETTINGS))
  const [logs, setLogs] = useState(() => load(LOGS_KEY, SEED_LOGS))

  useEffect(() => {
    localStorage.setItem(USERS_KEY, JSON.stringify(users))
  }, [users])
  useEffect(() => {
    localStorage.setItem(DOCUMENTS_KEY, JSON.stringify(documents))
  }, [documents])
  useEffect(() => {
    localStorage.setItem(INTEGRATIONS_KEY, JSON.stringify(integrations))
  }, [integrations])
  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
  }, [settings])
  useEffect(() => {
    localStorage.setItem(LOGS_KEY, JSON.stringify(logs))
  }, [logs])

  const logActivity = useCallback(
    (action, details, extra = {}) => {
      const entry = {
        id: genId('LOG'),
        action,
        category: extra.category || 'system',
        actor: user?.name || 'Système',
        actorRole: user?.role || 'system',
        target: extra.target || '',
        details,
        severity: extra.severity || 'info',
        ip: '192.168.1.' + Math.floor(Math.random() * 200 + 10),
        createdAt: new Date().toISOString(),
      }
      setLogs((prev) => [entry, ...prev].slice(0, 500))
    },
    [user]
  )

  const createUser = (data) => {
    const entry = {
      id: nextId(users, 'USR'),
      name: data.name,
      email: data.email,
      role: data.role,
      status: data.status || 'active',
      department: data.department || '',
      phone: data.phone || '',
      lastLogin: null,
      createdAt: new Date().toISOString(),
    }
    setUsers((prev) => [entry, ...prev])
    logActivity('user.create', `Création du compte ${entry.name} (${entry.email})`, {
      category: 'users',
      target: entry.id,
    })
    return entry
  }

  const updateUser = (id, data) => {
    const target = users.find((u) => u.id === id)
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, ...data } : u)))
    logActivity('user.update', `Modification du compte ${data.name || target?.name || id}`, {
      category: 'users',
      target: id,
      severity: 'warning',
    })
  }

  const deleteUser = (id) => {
    const target = users.find((u) => u.id === id)
    setUsers((prev) => prev.filter((u) => u.id !== id))
    logActivity('user.delete', `Suppression du compte ${target?.name || id}`, {
      category: 'users',
      target: id,
      severity: 'critical',
    })
  }

  const createDocument = (data) => {
    const entry = {
      id: nextId(documents, 'DOC'),
      title: data.title,
      type: data.type,
      category: data.category,
      language: data.language,
      status: data.status,
      content: data.content,
      views: 0,
      tags: data.tags || [],
      attachments: data.attachments || [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    setDocuments((prev) => [entry, ...prev])
    logActivity('document.create', `Création du document ${entry.title}`, {
      category: 'documents',
      target: entry.id,
    })
    return entry
  }

  const updateDocument = (id, data) => {
    const target = documents.find((d) => d.id === id)
    setDocuments((prev) =>
      prev.map((d) =>
        d.id === id
          ? { ...d, ...data, updatedAt: new Date().toISOString() }
          : d
      )
    )
    logActivity('document.update', `Modification du document ${data.title || target?.title || id}`, {
      category: 'documents',
      target: id,
      severity: 'warning',
    })
  }

  const deleteDocument = (id) => {
    const target = documents.find((d) => d.id === id)
    setDocuments((prev) => prev.filter((d) => d.id !== id))
    logActivity('document.delete', `Suppression du document ${target?.title || id}`, {
      category: 'documents',
      target: id,
      severity: 'critical',
    })
  }

  const addIntegration = (data) => {
    const entry = {
      id: nextId(integrations, 'INT'),
      provider: data.provider,
      name: data.name,
      type: data.type,
      enabled: false,
      status: 'disconnected',
      apiUrl: data.apiUrl || '',
      apiKey: data.apiKey || '',
      syncDirection: 'bidirectional',
      syncFrequency: 'realtime',
      lastSync: null,
    }
    setIntegrations((prev) => [...prev, entry])
    logActivity('integration.create', `Ajout de l'intégration ${entry.name}`, {
      category: 'integrations',
      target: entry.id,
    })
    return entry
  }

  const updateIntegration = (id, data) => {
    const target = integrations.find((i) => i.id === id)
    setIntegrations((prev) => prev.map((i) => (i.id === id ? { ...i, ...data } : i)))
    logActivity('integration.update', `Configuration mise à jour pour ${data.name || target?.name || id}`, {
      category: 'integrations',
      target: id,
      severity: 'warning',
    })
  }

  const toggleIntegration = (id) => {
    const target = integrations.find((i) => i.id === id)
    const next = !target?.enabled
    setIntegrations((prev) =>
      prev.map((i) =>
        i.id === id ? { ...i, enabled: next, status: next ? 'connected' : 'disconnected' } : i
      )
    )
    logActivity('integration.toggle', `${next ? 'Activation' : 'Désactivation'} de ${target?.name || id}`, {
      category: 'integrations',
      target: id,
      severity: next ? 'warning' : 'info',
    })
  }

  const deleteIntegration = (id) => {
    const target = integrations.find((i) => i.id === id)
    setIntegrations((prev) => prev.filter((i) => i.id !== id))
    logActivity('integration.delete', `Suppression de l'intégration ${target?.name || id}`, {
      category: 'integrations',
      target: id,
      severity: 'critical',
    })
  }

  const updateSettings = (data) => {
    setSettings((prev) => ({ ...prev, ...data }))
    logActivity('settings.update', 'Mise à jour des paramètres généraux', {
      category: 'settings',
      target: 'SETTINGS',
      severity: 'warning',
    })
  }

  const clearLogs = () => {
    setLogs([])
    logActivity('logs.clear', 'Journal d\'activité vidé', {
      category: 'logs',
      severity: 'critical',
    })
  }

  return (
    <AdminContext.Provider
      value={{
        users,
        documents,
        integrations,
        settings,
        logs,
        createUser,
        updateUser,
        deleteUser,
        createDocument,
        updateDocument,
        deleteDocument,
        addIntegration,
        updateIntegration,
        toggleIntegration,
        deleteIntegration,
        updateSettings,
        logActivity,
        clearLogs,
      }}
    >
      {children}
    </AdminContext.Provider>
  )
}

export default AdminContext
