# Page Dependency Trees

Dependencies list local visual modules first; contexts/services provide data and are included only where they shape rendered state.

## `/dashboard` (Dashboard)
Entry: `frontend/src/pages/Dashboard.jsx`
- `frontend/src/components/dashboard/StatCard.jsx`
- `frontend/src/components/tickets/constants.js`
- `frontend/src/contexts/useAuth.js`
- `frontend/src/contexts/useTickets.js`
- `frontend/src/contexts/useProducts.js`
- `frontend/src/components/layout/Layout.jsx`
  - `frontend/src/components/layout/LeftSidebar.jsx`
  - `frontend/src/components/layout/TopNavBar.jsx`

## `/tickets` (Ticket list)
Entry: `frontend/src/pages/tickets/TicketsList.jsx`
- `frontend/src/components/tickets/StatusBadge.jsx`
  - `frontend/src/components/tickets/constants.js`
- `frontend/src/components/tickets/PriorityBadge.jsx`
- `frontend/src/components/tickets/CategoryBadge.jsx`
- `frontend/src/contexts/useTickets.js`
- `frontend/src/contexts/useAuth.js`
- `frontend/src/contexts/useAdmin.js`
- `frontend/src/components/layout/Layout.jsx`
  - `frontend/src/components/layout/LeftSidebar.jsx`
  - `frontend/src/components/layout/TopNavBar.jsx`

## `/products` (Product catalog)
Entry: `frontend/src/pages/products/Products.jsx`
- `frontend/src/components/admin/ui.jsx`
  - `PageHeader`
- `frontend/src/components/products/ProductCard.jsx`
  - `frontend/src/components/products/WarrantyBadge.jsx`
- `frontend/src/components/products/CategoryFilter.jsx`
- `frontend/src/contexts/useProducts.js`
- `frontend/src/contexts/useAuth.js`
- `frontend/src/components/layout/Layout.jsx`
  - `frontend/src/components/layout/LeftSidebar.jsx`
  - `frontend/src/components/layout/TopNavBar.jsx`

## `/analytics` (Analytics)
Entry: `frontend/src/pages/analytics/Analytics.jsx`
- `frontend/src/components/analytics/charts.jsx`
- `frontend/src/contexts/useTickets.js`
- `frontend/src/contexts/useAuth.js`
- `frontend/src/components/layout/Layout.jsx`

## `/admin` (Administration overview and CRUD)
Entry: `frontend/src/pages/admin/AdminOverview.jsx`
- `frontend/src/pages/admin/AdminLayout.jsx`
- `frontend/src/components/admin/ui.jsx`
- `frontend/src/components/admin/badges.jsx`
- `frontend/src/contexts/useAdmin.js`
- `frontend/src/contexts/useAuth.js`
Related key entries: `AdminTickets.jsx`, `AdminUsers.jsx`, `UserForm.jsx`, `AdminDocuments.jsx`, `DocumentForm.jsx`, `AdminProducts.jsx`, `ProductForm.jsx`, `AdminIntegrations.jsx`, `AdminLogs.jsx`, `AdminSettings.jsx`.

## `/responsable-sav` (SAV management)
Entry: `frontend/src/pages/responsable-sav/ResponsableSAVOverview.jsx`
- `frontend/src/pages/responsable-sav/ResponsableSAVLayout.jsx`
- `frontend/src/components/admin/ui.jsx`
- `frontend/src/components/admin/badges.jsx`
- `frontend/src/pages/analytics/Analytics.jsx` (analytics child route)
- shared ticket/admin pages listed above for nested CRUD routes

## `/agent` (Support agent)
Entry: `frontend/src/pages/agent/AgentOverview.jsx`
- `frontend/src/pages/agent/AgentLayout.jsx`
- `frontend/src/pages/agent/AgentTicketsList.jsx`
- `frontend/src/pages/agent/AgentTicketDetail.jsx`
- `frontend/src/components/tickets/StatusBadge.jsx`
- `frontend/src/components/tickets/PriorityBadge.jsx`
- `frontend/src/components/admin/ui.jsx`
- `frontend/src/pages/analytics/Analytics.jsx` (analytics child route)

## Auth and secondary pages
- `/login`: `components/auth/Login.jsx` -> `useAuth`, auth API styles.
- `/signup`: `components/auth/Signup.jsx` -> `useAuth`.
- `/forgot-password`: `components/auth/forgot-password.jsx`.
- `/tickets/new`, `/tickets/:id`, `/tickets/:id/edit`: `TicketCreate.jsx`, `TicketDetail.jsx`, `TicketEdit.jsx`, `TicketForm.jsx`, ticket badges, `ProductSelector.jsx` where applicable.
- `/products/:id`: `ProductDetail.jsx`, `ProductCard.jsx`, `WarrantyBadge.jsx`.
- `/chat`, `/notifications`, `/settings`: respective page entries plus auth/context services.
