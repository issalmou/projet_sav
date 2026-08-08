# 3LM Soltuion AI | Portail Client - Guide d'Architecture

## Vue d'ensemble

Ce document explique la structure du portail client 3LM Soltuion AI, conçu pour offrir une expérience utilisateur fluide et intuitive pour la gestion des services, tickets et produits.

## Structure du Layout

### 1. Sidebar Gauche (`LeftSidebar`)

**Composant réutilisable** avec navigation principale.

| Élément | Icône | Description |
|---------|-------|-------------|
| Dashboard | `lucide:layout-dashboard` | Page d'accueil avec vue d'ensemble |
| Chat AI | `lucide:message-circle` | Assistant conversationnel |
| Tickets | `lucide:ticket` | Gestion des demandes support |
| Produits | `lucide:package` | Cataloge de produits |
| Base de connaissances | `lucide:book-open` | Documentation et guides |
| Analytiques | `lucide:bar-chart-2` | Statistiques et rapports |
| Notifications | `lucide:bell` | Centre de notifications |
| Administration | `lucide:shield` | Gestion admin (si applicable) |
| Paramètres | `lucide:settings` | Configuration du compte |

**États visuels :**
- Item actif : fond sombre + bordure bleue gauche
- Hover : léger changement de fond

### 2. Header (`TopNavBar`)

**Composant réutilisable** contenant :
- **Barre de recherche** : Recherche globale dans le portail
- **Notifications** : Icône avec badge de compteur
- **Profil utilisateur** : 
  - Avatar avec initiales
  - Nom complet
  - Rôle (ex: "Client Premium")

### 3. Zone Principale (`Main Content`)

Layout en grille responsive :
```
+------------------------------------------+
|           Welcome & Stats Widgets         |
+------------------------------------------+
|                    |                      |
|   Activités        |   Panneau Droit      |
|   Récentes         |   - Documentation    |
|                    |   - Knowledge Base   |
|   Produits         |   - Health Monitor   |
|   à la une         |                      |
|                    |                      |
+------------------------------------------+
```

## Widgets Clés (Statistiques)

### Tickets Ouverts
- **Valeur** : Nombre de tickets en cours
- **Tendance** : "Dernière mise à jour: Xh ago"
- **Icône** : `lucide:ticket`
- **Couleur** : Bleu

### Messages
- **Valeur** : Total des messages
- **Badge** : Nombre de non-lus
- **Icône** : `lucide:message-square-more`
- **Couleur** : Bleu

### Statut Système
- **Statut** : Opérationnel / Maintenance / Panne
- **Indicateur** : Point vert animé
- **Icône** : `lucide:activity`
- **Couleur** : Vert (opérationnel)

### Services Actifs
- **Valeur** : Nombre de services actifs
- **Info** : Date de prochain renouvellement
- **Icône** : `lucide:layers`
- **Couleur** : Indigo

## Navigation & Pages

### Page Dashboard (`/dashboard`)
- Widgets de statistiques
- Activités récentes
- Produits en vedette
- Panneau d'aide rapide

### Page Tickets (`/tickets`)
- Liste des tickets avec filtres
- Détail d'un ticket
- Création de nouveau ticket

### Page Chat AI (`/chat`)
- Interface conversationnelle
- Historique des conversations
- Suggestions contextuelles

### Page Produits (`/products`)
- Cataloge complet
- Détail produit
- Statut garantie

### Page Paramètres (`/settings`)
- Profil utilisateur
- Préférences
- Sécurité

## Système de Design

### Palette de Couleurs

| Variable | Valeur | Usage |
|----------|--------|-------|
| `--primary` | #2563EB | Actions principales |
| `--primary-dark` | #1E40AF | Hover states |
| `--text-primary` | #0F172A | Texte principal |
| `--text-secondary` | #64748B | Texte secondaire |
| `--background` | #F8FAFC | Fond de page |
| `--surface` | #FFFFFF | Cartes et surfaces |
| `--border` | #E2E8F0 | Bordures |

### Typographie
- **Police** : Inter (Google Fonts)
- **Poids** : 300, 400, 500, 600, 700

### Espacement
- Utilisation du système Tailwind : `p-4`, `p-6`, `p-8`, etc.
- Border radius : `rounded-xl`, `rounded-2xl`

### Ombres
- Cartes : `custom-shadow` (ombre subtile)
- Hover : `card-hover` (élévation au survol)

## Composants Réutilisables

### StatCard
```jsx
<StatCard 
  statValue="3"
  trendText="Dernière mise à jour: 2h ago"
  showTrend={true}
/>
```

### LeftSidebar
```jsx
<LeftSidebar 
  activeItem="dashboard"
  dashboardHref="#dashboard"
  chatHref="#chat"
  ticketsHref="#tickets"
  // ... autres props
/>
```

### TopNavBar
```jsx
<TopNavBar 
  userName="John Doe"
  userRole="Client Premium"
  userInitials="JD"
/>
```

## Responsivité

### Breakpoints
- **Mobile** : < 640px (1 colonne)
- **Tablette** : 640px - 1024px (2 colonnes)
- **Desktop** : > 1024px (3 colonnes)

### Adaptables
- Sidebar : rétractable sur mobile
- Widgets : passage de 4 à 2 à 1 colonne
- Grille principale : 2 colonnes → 1 colonne

## Interactions

### Transitions
- `card-hover` : translateY(-2px) + ombre accrue
- `transition-all` : toutes les propriétés
- `active:scale-[0.98]` : feedback tactile

### États
- Hover : changement de couleur de fond
- Focus : ring bleu avec opacité
- Active : légère réduction de scale

## Fichiers Sources

| Fichier | Description |
|---------|-------------|
| `src/App.jsx` | Routeur principal |
| `src/components/auth/Login.jsx` | Page de connexion |
| `src/components/auth/Signup.jsx` | Page d'inscription |
| `src/components/auth/forgot-password.jsx` | Récupération de mot de passe |
| `src/index.css` | Styles globaux et tokens |

## Prochaines Étapes

1. **Implémenter les pages manquantes** : Tickets, Chat, Produits, Paramètres
2. **Ajouter la logique de navigation** : React Router pour chaque section
3. **Connecter les données** : API pour les widgets et listes
4. **Optimiser la performance** : Lazy loading des routes
5. **Tests d'accessibilité** : ARIA labels, navigation clavier

---

*Document généré par Superdesign - Version 1.0*