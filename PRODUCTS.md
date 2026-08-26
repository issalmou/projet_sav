# Module Produits — Documentation Technique

## Vue d'ensemble

Le module Produits gère le cycle de vie complet des produits du parc SAV : CRUD, recherche, filtrage, garantie, historique d'achats et association aux tickets. Les données sont stockées en **localStorage** (pattern Context + useState identique à `TicketsContext`).

---

## Architecture des fichiers

```
src/
├── contexts/
│   ├── ProductsContext.jsx      # Provider + CRUD + seed data + categories
│   └── useProducts.js           # Hook d'accès au context
├── components/products/
│   ├── ProductCard.jsx          # Carte produit (grille + compact)
│   ├── ProductSelector.jsx      # Sélecteur réutilisable (modal + dropdown)
│   ├── WarrantyBadge.jsx        # Badge, dot, bordure de garantie
│   └── CategoryFilter.jsx       # Filtres horizontaux par catégorie
├── pages/products/
│   ├── Products.jsx             # Page liste (/products)
│   └── ProductDetail.jsx        # Fiche produit (/products/:id)
└── pages/tickets/
    └── TicketForm.jsx           # Intégration du sélecteur produit
```

---

## Modèle de données

### Produit

| Champ | Type | Description |
|-------|------|-------------|
| `id` | string | Identifiant unique (`PRD-001`, `PRD-002`...) |
| `reference` | string | Référence produit (ex: `NX-OLED-48293`) |
| `name` | string | Nom commercial |
| `category` | string | Catégorie (`Ecrans`, `Serveurs`, `Reseau`, `Impression`, `Stockage`, `Audio`, `Autre`) |
| `description` | string | Description textuelle |
| `brand` | string | Marque fabricante |
| `model` | string | Modèle technique |
| `serial_number` | string | Numéro de série |
| `price` | number | Prix unitaire en EUR |
| `image_url` | string\|null | Image en base64 (upload) ou null |
| `warranty_months` | number\|null | Durée de garantie en mois |
| `warranty_purchase_date` | string\|null | Date d'achat (format ISO `YYYY-MM-DD`) |
| `specs` | object | Caractéristiques techniques (clé/valeur libre) |
| `purchases` | Purchase[] | Historique des achats |
| `createdAt` | string | Date de création (ISO) |
| `updatedAt` | string | Dernière modification (ISO) |

### Purchase (Achat)

| Champ | Type | Description |
|-------|------|-------------|
| `id` | string | Identifiant unique (`PUR-001`...) |
| `date` | string | Date d'achat (`YYYY-MM-DD`) |
| `quantity` | number | Quantité achetée |
| `unit_price` | number | Prix unitaire |
| `supplier` | string | Nom du fournisseur |
| `invoice` | string | Numéro de facture |
| `notes` | string | Notes optionnelles |

---

## Catégories de produits

Définies dans `PRODUCT_CATEGORIES` (exportées depuis `ProductsContext.jsx`) :

| Value | Label | Icône | Couleur |
|-------|-------|-------|---------|
| `Ecrans` | Écrans | `monitor` | Indigo |
| `Serveurs` | Serveurs | `server` | Bleu |
| `Reseau` | Réseau | `wifi` | Violet |
| `Impression` | Impression | `printer` | Ambre |
| `Stockage` | Stockage | `hard-drive` | Emeraude |
| `Audio` | Audio | `headphones` | Rose |
| `Autre` | Autre | `package` | Gris |

> **Note** : Ces catégories sont distinctes des catégories de tickets (`Matériel`, `Logiciel`, etc. dans `constants.js`).

---

## Garantie — Logique de calcul

La garantie est calculée dynamiquement à partir de `warranty_purchase_date` + `warranty_months` :

```
Date fin = Date achat + warranty_months
```

### 4 statuts possibles

| Statut | Condition | Couleur | Icône |
|--------|-----------|---------|-------|
| `active` | Date fin > aujourd'hui + 30j | Teal 🟢 | `ShieldCheck` |
| `expiring` | Date fin > aujourd'hui mais < 30j | Orange 🟠 | `ShieldAlert` |
| `expired` | Date fin < aujourd'hui | Rouge 🔴 | `ShieldX` |
| `none` | Pas de date ou pas de mois définis | Gris ⚪ | `ShieldQuestion` |

### Fonction principale

```jsx
import { getWarrantyInfo } from 'components/products/WarrantyBadge'

const { status, label, color, dotColor, borderColor, endDate, icon } = getWarrantyInfo(
  product.warranty_purchase_date,
  product.warranty_months
)
```

Retourne un objet avec le statut, le label, les classes CSS, la date de fin et l'icône Lucide correspondante.

---

## Composants

### 1. `ProductsContext` — Provider de données

**Fichier** : `src/contexts/ProductsContext.jsx`

```jsx
import { ProductsProvider } from './contexts/ProductsContext'
// Fourni dans App.jsx, enveloppe toute l'application
```

**Méthodes exposées via `useProducts()` :**

| Méthode | Signature | Description |
|---------|-----------|-------------|
| `products` | state | Tableau de tous les produits |
| `getProduct` | `(id) => Product` | Récupère un produit par ID |
| `getProductsByCategory` | `(category) => Product[]` | Filtre par catégorie |
| `createProduct` | `(data) => Product` | Crée un produit (auto-ID) |
| `updateProduct` | `(id, data) => void` | Met à jour un produit |
| `deleteProduct` | `(id) => void` | Supprime un produit |
| `addPurchase` | `(productId, purchaseData) => Purchase` | Ajoute un achat à un produit |
| `searchProducts` | `(query, category?) => Product[]` | Recherche multi-champs |
| `categories` | `PRODUCT_CATEGORIES` | Liste des catégories |

**Recherche** : `searchProducts` recherche dans `name`, `reference`, `brand`, `description`, `serial_number`.

**Seed data** : 8 produits pré-chargés au premier chargement (localStorage vide). Les IDs suivent le format `PRD-XXX`.

**Persistance** : `localStorage` avec la clé `sav_products`. Sync automatique via `useEffect`.

---

### 2. `useProducts` — Hook d'accès

**Fichier** : `src/contexts/useProducts.js`

```jsx
const { products, getProduct, searchProducts, createProduct, ... } = useProducts()
```

Lance une erreur si utilisé en dehors d'un `ProductsProvider`.

---

### 3. `ProductCard` — Carte de produit

**Fichier** : `src/components/products/ProductCard.jsx`

**Props :**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `product` | Product | requis | Objet produit |
| `categoryIcon` | string | `'package'` | Nom de l'icône catégorie |
| `onClick` | func | `null` | Callback au clic (si null → navigue vers `/products/:id`) |
| `selected` | boolean | `false` | État sélectionné (bordure bleue + ring) |
| `highlighted` | boolean | `false` | État survolé au clavier |
| `compact` | boolean | `false` | Mode ligne (utilisé dans les sélecteurs) |

**Rendu visuel (mode grille) :**
- Image en haut (ou icône de catégorie en fallback)
- Badge garantie en overlay (coin supérieur droit)
- Compteur d'achats en overlay (coin inférieur gauche)
- Point de garantie (`WarrantyDot`) à côté du nom
- Bordure latérale colorée selon le statut de garantie (`border-l-4`)
- Badge catégorie + prix en bas

**Rendu visuel (mode compact) :**
- Ligne avec icône/image, nom, référence, prix
- Point de garantie à gauche du nom
- Bordure latérale colorée

---

### 4. `ProductSelector` — Sélecteur réutilisable

**Fichier** : `src/components/products/ProductSelector.jsx`

**Props :**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `open` | boolean | requis | Contrôle l'ouverture |
| `onClose` | func | requis | Callback de fermeture |
| `onSelect` | func | requis | Callback de sélection `(product) => void` |
| `selectedId` | string | `null` | ID du produit sélectionné |
| `mode` | `'modal'` \| `'dropdown'` | `'modal'` | Mode d'affichage |
| `showWarrantyFilter` | boolean | `true` | Afficher les filtres garantie |
| `filterWarranty` | string\|null | `null` | Filtrage par défaut |
| `placeholder` | string | `'Rechercher...'` | Texte du champ recherche |
| `multiple` | boolean | `false` | Sélection multiple |
| `selectedIds` | string[] | `[]` | IDs sélectionnés (mode multiple) |

**Modes :**

- **`modal`** : Overlay plein écran via `<Modal>` (composant `admin/ui.jsx`)
- **`dropdown`** : Menu déroulant positionné sous le déclencheur (absolute)

**Fonctionnalités :**
- Recherche en temps réel (nom, référence, marque, S/N)
- Filtres par catégorie (`CategoryFilter`)
- Filtres par statut de garantie (Toutes / Sous garantie / Expire bientôt / Expirée / Sans garantie)
- Navigation clavier : `↑↓` naviguer, `Entrée` sélectionner, `Esc` fermer
- Compteurs dynamiques sur chaque filtre
- Auto-reset des filtres à la fermeture

**Export nommé `ProductSelectorTrigger` :**

Composant déclencheur réutilisable qui affiche :
- Le produit sélectionné (nom, référence, bouton retrait au survol)
- Ou un placeholder avec bordure pointillée

```jsx
import ProductSelector, { ProductSelectorTrigger } from 'components/products/ProductSelector'

<ProductSelectorTrigger
  product={selectedProduct}
  onClick={() => setOpen(true)}
  onRemove={() => setSelected(null)}
/>
<ProductSelector open={open} onClose={() => setOpen(false)} onSelect={handleSelect} />
```

---

### 5. `WarrantyBadge` — Indicateurs de garantie

**Fichier** : `src/components/products/WarrantyBadge.jsx`

**Exports :**

| Export | Type | Description |
|--------|------|-------------|
| `getWarrantyInfo` | function | Calcule le statut et retourne { status, label, color, dotColor, borderColor, endDate, icon } |
| `WarrantyBadge` | component | Badge coloré avec icône + label (compact ou normal) |
| `WarrantyDot` | component | Point coloré minimal (xs/sm/md) |
| `WarrantyCardBorder` | component | Enfant avec bordure latérale colorée |

**Utilisation :**

```jsx
// Badge standard
<WarrantyBadge purchaseDate={product.warranty_purchase_date} warrantyMonths={product.warranty_months} />

// Badge compact (texte minuscule)
<WarrantyBadge purchaseDate={...} warrantyMonths={...} compact />

// Point minimal
<WarrantyDot purchaseDate={...} warrantyMonths={...} size="xs" />

// Bordure de carte
<WarrantyCardBorder purchaseDate={...} warrantyMonths={...}>
  <MonContenu />
</WarrantyCardBorder>
```

---

### 6. `CategoryFilter` — Filtres par catégorie

**Fichier** : `src/components/products/CategoryFilter.jsx`

**Props :**

| Prop | Type | Description |
|------|------|-------------|
| `value` | string\|null | Catégorie sélectionnée (null = toutes) |
| `onChange` | func | Callback `(categoryValue \| null) => void` |
| `productCounts` | object | `{ total: N, Ecrans: N, Serveurs: N, ... }` |

Affiche des boutons horizontaux avec icône, label et compteur. Les catégories vides sont masquées.

---

### 7. `Products.jsx` — Page liste

**Route** : `/products`

Fonctionnalités :
- Barre de recherche (nom, référence, marque)
- Filtres par catégorie (`CategoryFilter`)
- **Filtres par statut de garantie** (5 boutons avec compteurs)
- Grille responsive 1/2/3 colonnes de `ProductCard`
- Empty state adapté (filtres actifs vs aucun produit)
- Résumé des filtres actifs sous la barre de recherche

---

### 8. `ProductDetail.jsx` — Fiche produit

**Route** : `/products/:id`

**Layout 2 colonnes (colonne principale + sidebar) :**

**Colonne principale (gauche) :**
- `ImageUploader` : Upload d'image (drag/click, preview, suppression, validation 5 Mo, stockage base64)
- `Description` : Texte éditable inline en mode édition
- `PurchaseHistory` : Timeline des achats + formulaire d'ajout

**Sidebar (droite) :**
- `Informations` : Référence, marque, catégorie, S/N, modèle, prix (éditable en mode édition)
- `WarrantySection` : Barre de progression, dates achat/expiration, durée restante
- `SpecsSection` : Caractéristiques techniques (clé/valeur)
- Dates de création/modification

**Modes :**
- **Lecture** : Affichage formaté de toutes les informations
- **Édition** : Tous les champs deviennent des inputs éditables + bouton "Enregistrer"
- **Suppression** : Modal de confirmation (`ConfirmModal`)

---

## Intégration dans les tickets

Dans `TicketForm.jsx`, le champ "Produit associé" utilise :

```jsx
<ProductSelectorTrigger
  product={formData.product}
  onClick={() => setProductSelectorOpen(true)}
  onRemove={formData.product ? () => handleChange('product', null) : null}
/>
<ProductSelector
  open={productSelectorOpen}
  onClose={() => setProductSelectorOpen(false)}
  onSelect={(product) => handleChange('product', product)}
  selectedId={formData.product?.id}
  mode="modal"
/>
```

Le produit sélectionné est stocké dans `formData.product` (objet complet) et soumis avec les autres champs du ticket via `onSubmit({ ..., product: formData.product })`.

---

## Routes

| Route | Composant | Description |
|-------|-----------|-------------|
| `/products` | `Products` | Liste/search/filtrage des produits |
| `/products/:id` | `ProductDetail` | Fiche produit détaillée |

---

## Dépendances

- **Aucune dépendance externe ajoutée** — Tout utilise React, lucide-react (déjà installé), et les composants existants (`Modal`, `Field`, `ConfirmModal`, `PageHeader` depuis `admin/ui.jsx`)
- **localStorage** pour la persistance (clé `sav_products`)
- **React Router** pour la navigation (`useNavigate`, `useParams`)

---

## Seed Data

8 produits pré-chargés au premier lancement :

| ID | Nom | Catégorie | Prix | Garantie | Achats |
|----|-----|-----------|------|----------|--------|
| PRD-001 | 3LM Solution Pro 32" 4K OLED | Écrans | 1 299,99 € | 36 mois (active) | 2 achats |
| PRD-002 | Smart Gateway Hub X-1 | Réseau | 349,99 € | 24 mois (expirée) | 1 achat |
| PRD-003 | ProLiant DL380 Gen11 | Serveurs | 8 750,00 € | 60 mois (active) | 1 achat |
| PRD-004 | LaserJet Pro M404dn | Impression | 429,00 € | 12 mois (active) | 1 achat |
| PRD-005 | Synology DiskStation DS423+ | Stockage | 599,00 € | 36 mois (expirée) | 2 achats |
| PRD-006 | Jabra Speak 520 | Audio | 189,99 € | 24 mois (active) | 1 achat |
| PRD-007 | 3LM Solution Ultra 27" QHD | Écrans | 649,99 € | 36 mois (active) | 1 achat |
| PRD-008 | Catalyst 9300 48-Port | Réseau | 12 450,00 € | 120 mois (active) | 1 achat |

---

## Conventions de style

Tous les composants suivent les conventions existantes du projet :
- **Cartes** : `bg-white rounded-2xl border border-slate-200 custom-shadow`
- **Inputs** : `bg-slate-50 border border-slate-200 rounded-xl text-sm`
- **Boutons principaux** : `bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20`
- **Badges** : `px-2 py-0.5 text-[10px] font-bold uppercase rounded border`
- **Icônes** : Lucide React (déjà installé)
- **Pas de dépendances externes** ajoutées
