# Gestion des Tickets — Spécification

## Vue d'ensemble

La page **Tickets** est le centre de gestion des demandes de support client. Elle permet de créer, suivre, filtrer et résoudre les tickets de support technique, logiciel, matériel ou administratif.

---

## Fonctionnalités

### 1. Statistiques (en haut)
| Statistique | Description |
|-------------|-------------|
| Total Tickets | Nombre total de tickets dans le système |
| En cours | Tickets avec le statut "En cours" |
| Résolus | Tickets avec le statut "Résolu" |
| En attente | Tickets avec le statut "Ouvert" (marqués "Urgent") |

### 2. Barre de filtres
- **Recherche** : recherche par ID, titre ou description du ticket
- **Tri** : Plus récent / Plus ancien / Priorité / Statut / Titre (avec inversion de l'ordre)
- **Filtres étendus** :
  - **Statut** : Tous / Ouvert / En cours / Résolu / Fermé (pastilles avec compteurs)
  - **Priorité** : Toutes / Haute / Moyenne / Basse
  - **Catégorie** : Toutes / Matériel / Logiciel / Réseau / Facturation / Compte / Autre
- **Actions** : Réinitialiser, Exporter (CSV)
- **Pagination** : 8 tickets par page

### 3. Liste des tickets (tableau)
Chaque ligne affiche :
- **ID** du ticket (ex: `#TK-001`)
- **Titre** et description courte
- **Catégorie** : Matériel, Logiciel, Réseau, Facturation, Compte, Autre (badge coloré)
- **Statut** : Ouvert / En cours / Résolu / Fermé (badge coloré)
- **Priorité** : Haute / Moyenne / Basse (badge coloré)
- **Assigné à** : agent responsable
- **Date** de création
- **Nombre de messages** dans la conversation

Le clic sur une ligne ouvre la **page de détail** du ticket.

### 4. Détail du ticket (page `/tickets/:id`)
- En-tête : ID, statut, priorité, catégorie, titre
- **Timeline de statut** : progression visuelle Ouvert → En cours → Résolu → Fermé
- **Actions de statut** : boutons contextuels selon le statut (Marquer en cours, Marquer résolu, Fermer, Rouvrir)
- Boutons **Modifier** et **Supprimer** (avec confirmation)
- Métadonnées : assigné à, date de création, dernière activité, nombre de messages
- Description complète + pièces jointes
- **Conversation** : fil de messages + zone de réponse

### 5. Création de ticket (page `/tickets/new`)
Formulaire dédié : titre, description, catégorie, priorité, assigné. La création bascule le ticket en statut **Ouvert**.

### 6. Modification de ticket (page `/tickets/:id/edit`)
Formulaire pré-rempli : titre, description, catégorie, priorité, assigné et **statut** (sélecteur visuel de statuts).

### 7. État vide
- Quand aucun ticket n'existe : message explicatif + bouton créer
- Quand aucun résultat de recherche : message "aucun résultat"

---

## Modèle de données (Ticket)

```js
{
  id: "TK-001",           // Identifiant unique
  title: "Titre",         // Titre du ticket
  description: "...",     // Description détaillée
  status: "open",         // open | in_progress | resolved | closed
  priority: "high",       // high | medium | low
  category: "Matériel",   // Matériel | Logiciel | Réseau | Facturation | Compte | Autre
  assignee: "Agent",      // Nom de l'agent assigné
  createdAt: "2026-07-27T09:00:00.000Z",  // Date de création (ISO)
  updatedAt: "2026-07-28T10:00:00.000Z",  // Dernière mise à jour (ISO)
  attachments: [{ name: "...", size: "..." }], // Pièces jointes
  messages: [{
    id: "MSG-...",        // Identifiant du message
    author: "Nom",        // Auteur du message
    role: "client",       // client | agent
    content: "...",       // Contenu du message
    createdAt: "..."      // Date du message (ISO)
  }]
}
```

---

## Codes couleur

### Statuts
| Statut | Background | Texte | Bordure | Point |
|--------|-----------|-------|---------|-------|
| Ouvert | `bg-blue-50` | `text-blue-700` | `border-blue-200` | `bg-blue-500` |
| En cours | `bg-amber-50` | `text-amber-700` | `border-amber-200` | `bg-amber-500` |
| Résolu | `bg-teal-50` | `text-teal-700` | `border-teal-200` | `bg-teal-500` |
| Fermé | `bg-slate-100` | `text-slate-600` | `border-slate-200` | `bg-slate-400` |

### Priorités
| Priorité | Background | Texte | Bordure |
|----------|-----------|-------|---------|
| Haute | `bg-red-50` | `text-red-700` | `border-red-200` |
| Moyenne | `bg-orange-50` | `text-orange-700` | `border-orange-200` |
| Basse | `bg-slate-50` | `text-slate-600` | `border-slate-200` |

---

## Endpoints API attendus (Backend)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/tickets` | Liste tous les tickets (avec filtres query params) |
| `GET` | `/api/tickets/:id` | Détail d'un ticket |
| `POST` | `/api/tickets` | Créer un nouveau ticket |
| `PUT` | `/api/tickets/:id` | Mettre à jour un ticket |
| `DELETE` | `/api/tickets/:id` | Supprimer un ticket |
| `POST` | `/api/tickets/:id/messages` | Ajouter un message à un ticket |
| `GET` | `/api/tickets/stats` | Statistiques des tickets |

### Query params pour `GET /api/tickets`
- `search` — Recherche par ID ou titre
- `status` — Filtrer par statut
- `priority` — Filtrer par priorité
- `page` — Numéro de page
- `limit` — Nombre de résultats par page

---

## Intégrations

- **Chat AI** : un ticket peut être créé directement depuis le chatbot via l'agent IA
- **Notifications** : création/mise à jour de ticket déclenche une notification
- **Dashboard** : les stats des tickets alimentent les cartes du dashboard
- **Email** : envoi d'emails de confirmation à chaque changement de statut

---

## Fichiers

| Fichier | Rôle |
|---------|------|
| `src/pages/tickets/TicketsList.jsx` | Liste des tickets avec filtrage, tri et pagination |
| `src/pages/tickets/TicketDetail.jsx` | Page de détail d'un ticket (statuts, conversation) |
| `src/pages/tickets/TicketCreate.jsx` | Page de création d'un ticket |
| `src/pages/tickets/TicketEdit.jsx` | Page de modification d'un ticket |
| `src/pages/tickets/TicketForm.jsx` | Formulaire partagé création/modification |
| `src/contexts/TicketsContext.jsx` | État global des tickets (mock + localStorage, CRUD) |
| `src/contexts/useTickets.js` | Hook d'accès au contexte tickets |
| `src/components/tickets/StatusBadge.jsx` | Badge visuel de statut |
| `src/components/tickets/PriorityBadge.jsx` | Badge visuel de priorité |
| `src/components/tickets/CategoryBadge.jsx` | Badge visuel de catégorie |
| `src/components/tickets/StatusSelect.jsx` | Sélecteur visuel de statut |
| `src/components/tickets/constants.js` | Constantes statuts / priorités / catégories |
| `docs/TICKETS.md` | Ce fichier de spécification |
