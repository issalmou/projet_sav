# Routes

## Router
The router is declared in `frontend/src/App.jsx` using `BrowserRouter`, `Routes`, and `Route`. `AuthProvider`, notifications, admin, tickets, products, and toast providers wrap the route tree.

## Public routes
| URL | Component | Layout/guard |
|---|---|---|
| `/login` | `frontend/src/components/auth/Login.jsx` | `PublicRoute` |
| `/signup` | `frontend/src/components/auth/Signup.jsx` | `PublicRoute` |
| `/forgot-password` | `frontend/src/components/auth/forgot-password.jsx` | `PublicRoute` |

## General authenticated routes
Parent layout: `frontend/src/components/layout/Layout.jsx`, protected by `ProtectedRoute`.
| URL | Component |
|---|---|
| `/dashboard` | `frontend/src/pages/Dashboard.jsx` |
| `/chat` | `frontend/src/pages/ChatBot.jsx` |
| `/tickets` | `frontend/src/pages/tickets/TicketsList.jsx` |
| `/tickets/new` | `frontend/src/pages/tickets/TicketCreate.jsx` via `ClientGuard` |
| `/tickets/:id` | `frontend/src/pages/tickets/TicketDetail.jsx` |
| `/tickets/:id/edit` | `frontend/src/pages/tickets/TicketEdit.jsx` |
| `/products` | `frontend/src/pages/products/Products.jsx` |
| `/products/:id` | `frontend/src/pages/products/ProductDetail.jsx` |
| `/analytics` | `frontend/src/pages/analytics/Analytics.jsx` via `analytics.view` |
| `/notifications` | `frontend/src/pages/Notifications.jsx` |
| `/settings` | `frontend/src/pages/Settings.jsx` |
| `/knowledge` | Inline coming-soon page |

## Admin routes
Parent `/admin`, role `admin`, layout `frontend/src/pages/admin/AdminLayout.jsx`.
`/admin` -> `AdminOverview`; `/admin/tickets` -> `AdminTickets`; `/admin/users` and user forms -> `AdminUsers`/`UserForm`; `/admin/documents` and forms -> `AdminDocuments`/`DocumentForm`; `/admin/products` and forms -> `AdminProducts`/`ProductForm`; `/admin/integrations` -> `AdminIntegrations`; `/admin/logs` -> `AdminLogs`; `/admin/settings` -> `AdminSettings`. Permission guards apply per section.

## Responsable SAV routes
Parent `/responsable-sav`, role `manager`, layout `frontend/src/pages/responsable-sav/ResponsableSAVLayout.jsx`.
Index -> `ResponsableSAVOverview`; `analytics` -> `Analytics`; `tickets` -> `TicketsList`; `tickets/new` -> `ResponsableSAVTicketCreate`; ticket detail/edit reuse ticket pages; users/documents/products/forms reuse admin pages with `/responsable-sav` base path; logs -> `AdminLogs`.

## Agent routes
Parent `/agent`, role `agent`, layout `frontend/src/pages/agent/AgentLayout.jsx`.
Index -> `AgentOverview`; `tickets` -> `AgentTicketsList`; `tickets/:id` -> `AgentTicketDetail`; edit reuses `TicketEdit`; `analytics` -> `Analytics`; documents/forms and logs reuse admin pages with `/agent` base path.

`/` and unmatched paths redirect to `/login`.
