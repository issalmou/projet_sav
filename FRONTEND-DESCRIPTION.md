# Description du frontend

## 1. Présentation

Le frontend de la plateforme SAV est une application web de support client,
développée pour 3LM Solutions sous la marque Nexus AI. Elle permet aux
clients, agents support, responsables SAV et administrateurs de suivre les
tickets, consulter les produits, visualiser les indicateurs et administrer les
ressources de la plateforme.

Le code frontend se trouve dans le dossier `frontend/` et peut être exécuté
indépendamment du backend.

## 2. Technologies et outils utilisés

### Technologies principales

| Outil | Version déclarée | Utilisation |
| --- | --- | --- |
| JavaScript | ES Modules | Langage principal du frontend |
| React | `19.2.7` | Création de l'interface et des composants |
| React DOM | `19.2.7` | Montage de l'application dans le DOM |
| Vite | `8.1.1` | Serveur de développement et bundler de production |
| React Router DOM | `7.18.1` | Routage, navigation et routes protégées |
| Tailwind CSS | `4.3.2` | Mise en forme avec des classes utilitaires |
| Plugin Tailwind pour Vite | `4.3.2` | Intégration de Tailwind CSS dans Vite |
| Lucide React | `1.24.0` | Bibliothèque d'icônes utilisée dans l'interface |
| Chart.js | `4.5.1` | Moteur de génération des graphiques |
| react-chartjs-2 | `5.3.1` | Composants React pour Chart.js |

### Outils de développement et de qualité

| Outil | Version déclarée | Utilisation |
| --- | --- | --- |
| Node.js / npm | Requis pour l'installation et l'exécution | Gestion de l'environnement JavaScript |
| ESLint | `10.6.0` | Analyse statique et contrôle du code |
| `@eslint/js` | `10.0.1` | Configuration JavaScript recommandée pour ESLint |
| `eslint-plugin-react-hooks` | `7.1.1` | Vérification des règles React Hooks |
| `eslint-plugin-react-refresh` | `0.5.3` | Compatibilité avec React Fast Refresh et Vite |
| `@vitejs/plugin-react` | `6.0.3` | Support de React dans Vite |
| `globals` | `17.7.0` | Déclaration des globales du navigateur pour ESLint |
| Git | Projet versionné | Suivi des versions du code source |

### APIs et ressources externes utilisées

- `Fetch API` du navigateur pour les appels HTTP vers le backend.
- `WebSocket API` du navigateur pour les notifications en temps réel.
- `localStorage` pour conserver la session, les tickets, les produits, les utilisateurs et les paramètres de démonstration.
- Google Fonts, avec la police `Inter` importée dans `src/index.css`.
- Variables d'environnement Vite : `VITE_API_URL` et `VITE_WS_URL`.

## 3. Architecture de l'application

Le démarrage suit le flux suivant :

```text
index.html -> src/main.jsx -> src/App.jsx
```

- `src/main.jsx` monte l'application React avec `StrictMode`.
- `src/App.jsx` configure le routeur, les providers et l'ensemble des routes.
- Les contextes React centralisent les données et les actions métier.
- Les composants réutilisables sont séparés des pages fonctionnelles.

### Organisation des dossiers

```text
frontend/
├── public/                 # favicon et sprites d'icônes
├── src/
│   ├── api/                # appels HTTP vers le backend
│   ├── components/         # composants réutilisables et formulaires
│   ├── contexts/           # états partagés et hooks associés
│   ├── pages/              # écrans de l'application
│   ├── services/           # WebSocket, notifications toast et données de démo
│   ├── App.jsx             # providers et routes
│   ├── main.jsx            # point d'entrée
│   └── index.css           # styles globaux et configuration Tailwind
├── eslint.config.js        # configuration ESLint
├── package.json            # scripts et dépendances
└── vite.config.js          # configuration Vite, React et Tailwind
```

## 4. Fonctionnalités frontend

### Authentification et accès

- Connexion, inscription et récupération de mot de passe.
- Authentification via les endpoints REST `/api/auth/login` et `/api/auth/me`.
- Conservation de l'utilisateur courant dans `localStorage`.
- Redirection automatique selon le rôle de l'utilisateur.
- Contrôle d'accès par permissions avec les rôles suivants : administrateur,
  responsable SAV, agent support et client.

### Gestion des tickets SAV

- Liste, détail, création, modification et suppression de tickets.
- Gestion du statut, de la priorité, de la catégorie, de l'assignation et des
  messages associés.
- Filtrage de l'affichage selon le rôle et l'utilisateur connecté.
- Composants réutilisables pour les badges de statut, priorité et catégorie.

### Gestion des produits

- Catalogue de produits et page de détail.
- Recherche par nom, référence, marque, description ou numéro de série.
- Filtrage par catégorie.
- Affichage des informations de garantie.
- Gestion administrative des produits et des achats associés.

### Tableaux de bord et analytique

- Tableau de bord client avec statistiques, activités récentes et produits.
- Espace responsable SAV et espace agent support.
- Espace d'administration pour les utilisateurs, documents, produits,
  intégrations, journaux et paramètres.
- Graphiques de tickets par statut, satisfaction client, incidents par produit
  et évolution temporelle.
- Récupération des métriques via `GET /api/dashboard/metrics`.
- Génération de métriques de démonstration lorsque le backend n'est pas
  disponible.

### Notifications et expérience utilisateur

- Notifications persistées localement.
- Connexion WebSocket authentifiée pour les notifications temps réel.
- Reconnexion automatique avec délai progressif et heartbeat.
- Messages toast de succès, d'information et d'erreur.
- Navigation responsive avec barre latérale et barre supérieure.

## 5. Gestion de l'état et des données

L'état partagé est géré avec l'API Context de React :

- `AuthContext` : utilisateur, connexion, déconnexion et profil.
- `TicketsContext` : tickets et messages.
- `ProductsContext` : catalogue, catégories et achats.
- `NotificationsContext` : notifications et état de la connexion WebSocket.
- `AdminContext` : utilisateurs, documents, intégrations, paramètres et logs.

Les données de tickets, produits et administration sont actuellement
persistées côté navigateur avec `localStorage`. Les données analytiques peuvent
être chargées depuis le backend ou générées localement pour la démonstration.

## 6. Routage et protection

Les routes publiques sont `/login`, `/signup` et `/forgot-password`. Les
routes applicatives sont protégées par `ProtectedRoute`, tandis que les
permissions spécifiques sont vérifiées par `Guard`.

Principaux espaces accessibles :

- `/dashboard`, `/tickets`, `/products`, `/chat`, `/notifications` et
  `/settings` pour l'application générale.
- `/analytics` pour les utilisateurs autorisés.
- `/admin` pour l'administration.
- `/responsable-sav` pour le responsable SAV.
- `/agent` pour l'agent support.

## 7. Styles et interface

- Tailwind CSS est importé via `@import "tailwindcss"` et le plugin Vite.
- Les classes utilitaires sont principalement utilisées directement dans le
  JSX.
- `src/index.css` définit les variables de couleurs, la police Inter, les
  dégradés de marque, les effets de focus, les ombres et les animations toast.
- Lucide React fournit les icônes des menus, formulaires, badges et tableaux de
  bord.

## 8. Commandes disponibles

Depuis le dossier `frontend/` :

```bash
npm install       # installe les dépendances
npm run dev       # démarre le serveur de développement Vite
npm run build     # génère la version de production dans dist/
npm run preview   # sert la build de production localement
npm run lint      # exécute ESLint
```

## 9. Configuration par environnement

Par défaut, les appels API utilisent `http://localhost:5000`. Cette valeur
peut être remplacée avec :

```text
VITE_API_URL=https://adresse-du-backend
VITE_WS_URL=wss://adresse-du-backend/ws/notifications
```

Lorsque `VITE_WS_URL` n'est pas défini, l'URL WebSocket est dérivée de
`VITE_API_URL` en remplaçant `http` par `ws` et en ajoutant
`/ws/notifications`.

## 10. Limites actuelles

- Certaines données métier sont encore simulées ou stockées localement côté
  frontend.
- La base de connaissances affiche encore une page placeholder.
- Les tests automatisés présents dans le dépôt concernent principalement le
  backend ; aucun framework de tests frontend n'est déclaré dans
  `package.json`.
