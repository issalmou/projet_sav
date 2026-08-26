# Tableau de bord Responsable SAV — Guide explicatif

## Vue d'ensemble

Le tableau de bord Responsable SAV est une page dédiée au pilotage du service
après-vente. Elle affiche les indicateurs clés (KPI) et des graphiques,
alimentés **en temps réel** depuis l'API backend.

Indicateurs fournis :
- Nombre de tickets par statut
- Temps de résolution moyen
- Taux de satisfaction client
- Incidents par produit
- Évolution des tickets créés / résolus (7 derniers jours)

Accès : route `/analytics`, réservée aux rôles **administrateur**, **responsable
SAV** et **agent** (permission `analytics.view`).

---

## Architecture des fichiers

```
src/
├── api/
│   └── analytics.js                  # Client API (GET /api/dashboard/metrics)
├── components/
│   └── analytics/
│       └── charts.jsx                # Configuration + composants Chart.js
├── pages/
│   └── analytics/
│       └── Analytics.jsx             # Page Responsable SAV
└── services/
    └── demoAnalytics.js              # Données de secours (API indisponible)
```

### 1. `src/api/analytics.js`

Point d'entrée réseau de la page. Il interroge l'endpoint d'agrégation avec le
token JWT de l'utilisateur :

```js
export async function getMetricsRequest({ token, signal }) {
  const response = await fetch(`${API_URL}/api/dashboard/metrics`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    signal,
  })
  // ...
}
```

- `token` : token d'accès (`user.access_token`).
- `signal` : `AbortController` pour annuler une requête en cours.

### 2. `src/components/analytics/charts.jsx`

Configure **Chart.js** une seule fois au chargement du module (enregistrement
des éléments, échelles, plugins et police `Inter`) puis exporte quatre
composants :

| Composant | Type Chart.js | Données affichées |
| --- | --- | --- |
| `StatusBarChart` | Barres verticales | Tickets par statut |
| `SatisfactionChart` | Anneau (doughnut) | Score CSAT + répartition satisfaits/neutres/mécontents |
| `IncidentsChart` | Barres horizontales | Incidents par produit |
| `TrendChart` | Courbes (line) | Créés vs résolus sur 7 jours |

Le score central de l'anneau (ex. `4.3/5`) est rendu par le plugin maison
`centerTextPlugin`.

### 3. `src/pages/analytics/Analytics.jsx`

Page principale. Elle contient :

- **En-tête** : titre, indicateur « Temps réel / Mode démo », horodatage de la
  dernière mise à jour, bouton « Actualiser ».
- **4 KPI** : Total Tickets, Tickets en attente, Temps moyen de résolution,
  Taux de satisfaction.
- **Graphiques** : tickets par statut, satisfaction client, incidents par
  produit, évolution sur 7 jours.

### 4. `src/services/demoAnalytics.js`

Génère des données réalistes **uniquement** lorsque l'API est injoignable
(backend non démarré en local), afin que la page reste utilisable en
développement. Chaque appel produit de légères variations pour illustrer le
rafraîchissement temps réel.

---

## Mécanisme temps réel

La page rafraîchit ses données par **polling** et sur événements de visibilité :

- Polling toutes les **30 secondes** (`REFRESH_INTERVAL_MS`).
- Re-fetch automatique au **focus** de la fenêtre et au retour sur l'onglet
  (`visibilitychange`).
- Bouton « Actualiser » pour un rafraîchissement manuel.
- Une requête en cours est **annulée** (`AbortController`) avant chaque nouvel
  appel pour éviter les réponses obsolètes.

État de connexion affiché en haut de page :
- **Temps réel** (pastille verte) : l'API répond et fournit les données.
- **Mode démo** (pastille ambre) : l'API est indisponible, données simulées.

---

## Filtrage par période

La page propose un sélecteur de période **Jour / Semaine / Mois / Personnalisé**
placé sous l'en-tête :

- **Jour** : tendance heure par heure sur 24 points.
- **Semaine** (défaut) : 7 derniers jours.
- **Mois** : 30 derniers jours.
- **Personnalisé** : plage de dates libre (champs « Du » / « Au », bornés à
  aujourd'hui). La tendance s'adapte au nombre de jours sélectionnés (90 max).

Le changement de période déclenche immédiatement une nouvelle requête API, puis
le polling repart sur la nouvelle période. Les libellés des cartes et la courbe
d'évolution reflètent la période active.

Côté API, la période est transmise en paramètres de requête :

```
GET /api/dashboard/metrics?period=week
GET /api/dashboard/metrics?period=day
GET /api/dashboard/metrics?period=month
GET /api/dashboard/metrics?period=custom&from=2026-08-01&to=2026-08-15
```



## Contrat de l'API

L'endpoint à implémenter côté backend (à la place du placeholder actuel
`api/dashboard.py`) doit renvoyer la structure suivante :

```json
{
  "generated_at": "2026-08-15T10:00:00Z",
  "total_tickets": 148,
  "tickets_by_status": {
    "open": 22,
    "in_progress": 18,
    "resolved": 89,
    "closed": 19
  },
  "avg_resolution_hours": 18.5,
  "csat": {
    "score": 4.3,
    "rated_count": 86,
    "satisfied": 74,
    "neutral": 8,
    "unsatisfied": 4
  },
  "incidents_by_product": [
    { "product": "Monitor Pro 32\" 4K OLED", "incidents": 34 },
    { "product": "Smart Gateway Hub X-1", "incidents": 28 }
  ],
  "trend": [
    { "date": "09/08", "created": 18, "resolved": 15 }
  ]
}
```

---

## Dépendances

Chart.js est installé via `react-chartjs-2` (wrapper React officiel) :

```bash
npm install chart.js react-chartjs-2
```

Versions ajoutées dans `package.json` : `chart.js ^4.5.1`, `react-chartjs-2 ^5.3.1`.

---

## Accès et permissions

- `src/contexts/roles.js` : permission `analytics.view` ajoutée pour
  `['admin', 'manager', 'agent']`.
- `src/App.jsx` : la route `/analytics` est protégée par `<Guard
  permission="analytics.view">`.
- `src/components/layout/LeftSidebar.jsx` : l'entrée « Analytiques » n'est
  visible que pour ces rôles.

---

## Vérifications

```bash
npm run lint    # eslint : aucun problème
npm run build   # build Vite : succès
```
