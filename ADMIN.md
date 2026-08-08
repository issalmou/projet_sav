# Module Administration — Guide explicatif

Ce document décrit le fonctionnement du module d'administration du SAV frontend :
contrôle d'accès par rôle, gestion des utilisateurs, base documentaire, intégrations,
logs d'activité et paramètres.

## 1. Architecture générale

Le module est organisé en 3 couches :

- **Contexte / état** : `src/contexts/AdminContext.jsx` (+ hook `src/contexts/useAdmin.js`)
  centralise toutes les données admin (utilisateurs, documents, intégrations, paramètres,
  logs) avec persistance en `localStorage`. La source de vérité des rôles et permissions
  est `src/contexts/roles.js`.
- **Composants partagés** : `src/components/admin/` — primitives UI (`ui.jsx`), badges
  (`badges.jsx`) et notifications (`useToast.jsx`).
- **Pages** : `src/pages/admin/` — une page par écran, toutes routées sous `/admin` et
  protégées par un garde de permission (`Guard` dans `src/App.jsx`).

## 2. Rôles et permissions

Définis dans `src/contexts/roles.js`.

| Rôle | Accès administration |
|------|----------------------|
| `admin` | Accès complet à tous les écrans `/admin/*` |
| `agent` | Accès à `/admin` (vue d'ensemble, base documentaire, intégrations, logs) mais **pas** aux utilisateurs ni aux paramètres |
| `client` | Aucun accès — redirection vers `/dashboard` |

La règle de visibilité est : `can(user, permission)`. Les permissions utilisées sont
`admin.view`, `users.manage`, `documents.manage`, `integrations.manage`, `logs.view`,
`settings.manage`.

> **Test rapide** : sur la page de connexion (`/login`), le sélecteur « Rôle de
> démonstration » permet de changer de rôle sans backend.

## 3. Les pages

### 3.1 Vue d'ensemble — `/admin` (`AdminOverview.jsx`)
Tableau de bord : KPI (utilisateurs actifs, documents publiés, intégrations connectées,
événements critiques), activité récente, santé des intégrations et actions rapides.

### 3.2 Utilisateurs — `/admin/users` (`AdminUsers.jsx` + `UserForm.jsx`)
CRUD complet :
- **Créer** : bouton « Nouvel utilisateur » → formulaire (nom, email, rôle, statut,
  mot de passe généré) avec validation.
- **Lire** : tableau avec recherche, filtres (rôle, statut) et pagination (8/ligne).
- **Mettre à jour** : icône crayon → formulaire pré-rempli → `updateUser`.
- **Supprimer** : icône corbeille → confirmation (`ConfirmModal`) → `deleteUser`
  (interdit pour l'utilisateur connecté, log en sévérité `critical`).

### 3.3 Base documentaire — `/admin/documents` (`AdminDocuments.jsx` + `DocumentForm.jsx`)
Gestion des FAQ, manuels et guides :
- CRUD complet (créer, lister/rechercher/filtrer, modifier, supprimer).
- **Upload de fichiers** (PDF, PNG, JPG, WEBP) : zone de glisser-déposer ou sélecteur
  de fichiers dans `DocumentForm.jsx`, avec validation de type et taille (2 Mo max,
  3 fichiers max). Les fichiers sont stockés en base64 (démo sans backend) et affichés
  dans le tableau avec un indicateur `📎 n`.
- **Suppression de fichiers** : bouton « X » sur chaque fichier joint (avant enregistrement
  ou en modification), plus suppression du document complet.
- KPI : total, publiés, brouillons, vues cumulées.

### 3.4 Intégrations CRM/ERP — `/admin/integrations` (`AdminIntegrations.jsx`)
- Liste des connexions sous forme de cartes (type, statut, dernière synchronisation).
- Ajout / suppression d'une intégration, activation par interrupteur (`Toggle`).
- Bouton « Tester la connexion » qui simule une vérification et journalise le résultat.

### 3.5 Logs d'activité — `/admin/logs` (`AdminLogs.jsx`)
Journal de toutes les actions réalisées sur la plateforme :
- **Filtres** : recherche libre (action, acteur, cible), catégorie, sévérité,
  **utilisateur** (liste des acteurs), **action** (liste des actions) et
  **plage de dates** (de / à).
- Affichage : date/heure, événement, catégorie, sévérité, IP, pagination (10/ligne).
- **Export CSV** (avec BOM UTF-8) et **« Vider le journal »** (réservé aux admins).
- Bannière d'alerte quand des événements critiques sont présents.

### 3.6 Paramètres globaux — `/admin/settings` (`AdminSettings.jsx`)
- Informations générales (nom de l'organisation, contact).
- Système & automatisations (mode maintenance, messages auto, SLA).
- Notifications par e-mail (alertes critiques, résumés, etc.).
- Sécurité (authentification à deux facteurs, politique de mot de passe).
- Paramètres de langue et fuseau horaire.

### 3.7 Paramètres personnels — `/settings` (`Settings.jsx`)
Profil de l'utilisateur connecté (nom, e-mail, mot de passe, préférences de
notifications) via `updateProfile` dans `src/contexts/AuthContext.jsx`.

## 4. Données et persistance

- Toutes les données sont mockées dans `AdminContext.jsx` (seed `SEED_*` : utilisateurs
  `USR-001..005`, documents `DOC-001..005`, intégrations `INT-001..003`, logs
  `LOG-001..005`).
- Chaque mutation (création, modification, suppression) appelle `logActivity(...)` pour
  tracer automatiquement l'action dans le journal (500 entrées maximum).
- Le stockage est en `localStorage` ; aucune API backend n'est encore branchée.

## 5. Navigation

- Le menu **Administration** est visible dans la barre latérale pour les rôles `admin`
  et `agent` (`src/components/layout/LeftSidebar.jsx`).
- La sous-navigation est filtrée par permission dans `AdminLayout.jsx`.
- `src/App.jsx` enveloppe les routes avec `AdminProvider` et protège `/admin/*` par le
  composant `Guard` (redirige vers `/admin` si `admin.view`, sinon vers `/dashboard`).

## 6. Vérifier que tout fonctionne

```bash
npm run dev        # lancer en développement
npm run lint       # vérifier le style
npm run build      # build de production
```

Parcours de test : connexion en admin → `/admin` → créer/modifier/supprimer un
utilisateur → créer un document avec un fichier PDF/image joint → vérifier le log
généré → tester les filtres des logs → exporter le CSV.
