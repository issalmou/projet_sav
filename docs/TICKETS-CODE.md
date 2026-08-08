# Module Tickets — Guide du code

## Vue d'ensemble

La partie "tickets" du projet est organisée en trois zones :

```
src/
├── contexts/
│   ├── TicketsContext.jsx        # État global des tickets (Provider)
│   └── useTickets.js             # Hook d'accès au contexte
├── components/
│   └── tickets/                  # Composants visuels réutilisables
│       ├── constants.js          # Constantes statuts / priorités / catégories
│       ├── StatusBadge.jsx       # Badge de statut (icône + libellé)
│       ├── PriorityBadge.jsx     # Badge de priorité
│       ├── CategoryBadge.jsx     # Badge de catégorie
│       └── StatusSelect.jsx      # Sélecteur visuel de statut (pastilles)
└── pages/
    └── tickets/                  # Pages reliées aux routes
        ├── TicketsList.jsx       # /tickets
        ├── TicketDetail.jsx      # /tickets/:id
        ├── TicketCreate.jsx      # /tickets/new
        ├── TicketEdit.jsx        # /tickets/:id/edit
        └── TicketForm.jsx        # Formulaire partagé création/modification
```

---

## 1. `src/contexts/useTickets.js`

Ce fichier est le **point d'entrée** pour lire et modifier les tickets depuis n'importe quel composant.

```js
import { useContext } from 'react'
import TicketsContext from './TicketsContext'

export function useTickets() {
  const context = useContext(TicketsContext)
  if (!context) {
    throw new Error('useTickets must be used within a TicketsProvider')
  }
  return context
}
```

### Rôle
- Récupère la valeur exposée par `TicketsContext` via `useContext`.
- **Garde-fou** : si le hook est utilisé hors du `<TicketsProvider>`, une erreur explicite est levée immédiatement (plutôt qu'un crash silencieux plus tard).
- Renvoie l'objet complet du contexte.

### Utilisation

```jsx
import { useTickets } from '../../contexts/useTickets'

function MonComposant() {
  const { tickets, getTicket, createTicket, updateTicket, deleteTicket, addMessage } = useTickets()
  // ...
}
```

---

## 2. `src/contexts/TicketsContext.jsx`

Crée le contexte React et fournit l'état global des tickets.

### État
- `useState` initialisé à partir de `localStorage` (clé `sav_tickets`). Si rien n'est stocké (ou si la donnée est corrompue), l'état démarre vide `[]`.
- Chaque modification de `tickets` est persistée automatiquement dans `localStorage` via `useEffect`.

### API exposée

| Méthode | Signature | Description |
|---------|-----------|-------------|
| `tickets` | `Ticket[]` | Liste complète des tickets |
| `getTicket` | `(id) => Ticket \| undefined` | Recherche un ticket par son ID |
| `createTicket` | `(data) => Ticket` | Crée un ticket (statut forcé `open`) et le renvoie |
| `updateTicket` | `(id, data) => void` | Fusionne `data` dans le ticket et met à jour `updatedAt` |
| `deleteTicket` | `(id) => void` | Supprime le ticket correspondant |
| `addMessage` | `(id, { author, role, content }) => void` | Ajoute un message à la conversation du ticket |

### Points clés
- **Génération d'ID** : `newId()` calcule le plus grand numéro `TK-###` existant et l'incrémente (`TK-001`, `TK-002`, ...).
- **Génération de message** : `newMessage()` crée un message avec un ID unique (`Date.now()` + aléatoire) et un `createdAt` ISO.
- **Mises à jour immuables** : toutes les mutations passent par `setTickets(prev => ...)` avec des mises à jour fonctionnelles, sans jamais muter l'état existant.

---

## 3. `src/components/tickets/` — Composants réutilisables

### `constants.js`
Source unique des valeurs métier :
- `STATUSES` : 4 statuts (`open`, `in_progress`, `resolved`, `closed`) avec libellé, couleurs Tailwind, point de couleur et `step` (ordre de progression 0→3).
- `STATUS_ORDER` : ordre canonique des statuts pour l'affichage et le tri.
- `PRIORITIES` : 3 priorités avec `rank` (0→2) pour le tri.
- `CATEGORIES` : 6 catégories avec couleurs de badge.
- `categoryColor(category)` : retourne la classe de couleur d'une catégorie.
- `STATUS_OPTIONS`, `PRIORITY_OPTIONS`, `SORT_OPTIONS` : listes pour les sélecteurs et le tri.

### `StatusBadge.jsx` / `PriorityBadge.jsx` / `CategoryBadge.jsx`
Badges visuels (pastilles arrondies) avec icône/libellé, disponibles en tailles `sm`, `md`, `lg`. Ils lisent les couleurs depuis `constants.js`.

### `StatusSelect.jsx`
Sélecteur de statut en grille de pastilles cliquables. La pastille active affiche la couleur du statut (`s.color`) et un anneau `ring` de la même teinte. Utilisé dans le formulaire de modification.

---

## 4. `src/pages/tickets/` — Pages et routes

### `TicketsList.jsx` (`/tickets`)
- Recherche (ID, titre, description), filtres (statut, priorité, catégorie), tri (date, priorité, statut, titre) avec inversion d'ordre.
- 4 cartes de statistiques calculées depuis `tickets`.
- Pagination (8 par page) et export CSV des résultats filtrés.
- Clic sur une ligne → `navigate('/tickets/:id')`.

### `TicketDetail.jsx` (`/tickets/:id`)
- Récupère le ticket via `getTicket(id)` (de `useParams()`).
- Timeline visuelle de statut + boutons de transition contextuels.
- Boutons Modifier / Supprimer (avec confirmation), métadonnées, description, pièces jointes.
- Conversation (fil de messages) + zone de réponse via `addMessage`.
- État "ticket introuvable" si `getTicket` renvoie `undefined`.

### `TicketForm.jsx` (composant partagé)
Formulaire unique piloté par les props :
- `mode` : `'create'` | `'edit'`
- `initialValues` : valeurs de départ (requis en mode `edit`)
- `onSubmit(values)` : callback appelé avec les données validées
- `submitLabel` : texte du bouton

Le champ **statut** (via `StatusSelect`) n'apparaît qu'en mode `edit` ; en création le statut est forcé à `open` par `createTicket`.

### `TicketCreate.jsx` (`/tickets/new`)
Enveloppe `TicketForm` : `onSubmit` appelle `createTicket(values)` puis redirige vers `/tickets/:id`.

### `TicketEdit.jsx` (`/tickets/:id/edit`)
Enveloppe `TicketForm` : charge le ticket via `getTicket(id)`, `onSubmit` appelle `updateTicket(id, values)` puis redirige vers `/tickets/:id`.

---

## 5. Flux de données

```
TicketForm (create) ──► createTicket ──► setTickets ──► localStorage
                                                     └──► ré-rendu de l'UI (list, stats, détail)

TicketDetail ──► updateTicket / addMessage / deleteTicket ──► setTickets ──► même flux
```

Le `TicketsProvider` est monté dans `App.jsx`, à l'intérieur de `AuthProvider`, ce qui rend `useTickets()` disponible sur **toutes** les routes (listes, détail, formulaires).

---

## 6. À retenir
- Toujours passer par `useTickets()` pour lire ou modifier les tickets (jamais accéder directement à `localStorage`).
- Les ID (`TK-###`) et les IDs de messages sont générés automatiquement, ne pas les définir manuellement.
- Le formulaire création/modification est partagé : ajouter un champ = le modifier dans `TicketForm.jsx` uniquement.
- `constants.js` centralise libellés et couleurs : pour ajouter un statut/catégorie, c'est là qu'il faut intervenir.
