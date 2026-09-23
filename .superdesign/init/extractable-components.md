# Extractable Components

## Layout Components
### `AppShell`
- Source: `frontend/src/components/layout/Layout.jsx`
- Category: layout
- Description: Authenticated two-column shell with sidebar, top navigation, and route outlet.
- Extractable props: none; navigation comes from router/auth context.
- Hardcoded: `LeftSidebar`, `TopNavBar`, flex sizing, min-height.

### `NavBar`
- Source: `frontend/src/components/layout/LeftSidebar.jsx`
- Category: layout
- Description: Dark 3LM Solutions sidebar with role-aware navigation and logout.
- Extractable props: active route is router state; no explicit component props.
- Hardcoded: logo, menu labels, icon mapping, Tailwind classes.

### `TopNavBar`
- Source: `frontend/src/components/layout/TopNavBar.jsx`
- Category: layout
- Description: Search header with notification and user dropdowns.
- Extractable props: `unreadCount` and `connectionStatus` are context-driven state candidates; navigation targets are fixed.
- Hardcoded: search placeholder, French labels, icon names, menu styling.

### `RoleLayout`
- Source: `frontend/src/pages/admin/AdminLayout.jsx`, `frontend/src/pages/agent/AgentLayout.jsx`, `frontend/src/pages/responsable-sav/ResponsableSAVLayout.jsx`
- Category: layout
- Description: Role-specific management header, permission-filtered pill navigation, logout, and outlet.
- Extractable props: `title`, `description`, `accentColor`, `icon`, `sections`.
- Hardcoded: role labels and section definitions in the current implementation.

## Basic Components
### `PageHeader`
- Source: `frontend/src/components/admin/ui.jsx`
- Category: basic
- Description: Heading/subtitle row with optional right-side actions.
- Extractable props: `title`, `subtitle`, `actions`.
- Hardcoded: typography classes.

### `StatCard`
- Source: `frontend/src/components/dashboard/StatCard.jsx`
- Category: basic
- Description: Dashboard KPI card with icon, value, trend or subtitle.
- Extractable props: `title`, `value`, `subtitle`, `trend`, `icon`, `color`.
- Hardcoded: icon/color maps and card styling.

### `Badge`
- Source: `frontend/src/components/admin/badges.jsx`
- Category: basic
- Description: Generic rounded pill used by role, document, severity, status, and integration badges.
- Extractable props: `className`, `children`.
- Hardcoded: pill geometry and typography.

### `TicketStatusBadge`
- Source: `frontend/src/components/tickets/StatusBadge.jsx`
- Category: basic
- Description: Icon-led ticket status pill with size variants.
- Extractable props: `status`, `size`.
- Hardcoded: status labels, icons, and token maps.

### `PriorityBadge`
- Source: `frontend/src/components/tickets/PriorityBadge.jsx`
- Category: basic
- Description: Priority pill with colored dot and size variants.
- Extractable props: `priority`, `size`.
- Hardcoded: priority labels and colors.

### `CategoryBadge`
- Source: `frontend/src/components/tickets/CategoryBadge.jsx`
- Category: basic
- Description: Ticket category pill with tag icon.
- Extractable props: `category`, `size`.
- Hardcoded: category color mapping and icon.

### `ProductCard`
- Source: `frontend/src/components/products/ProductCard.jsx`
- Category: basic
- Description: Product catalog card with image/icon, category, reference, purchases, and warranty state.
- Extractable props: `product`, `categoryIcon`, `onClick`, `selected`, `highlighted`, `compact`.
- Hardcoded: category color map, icon map, French labels, Tailwind classes.

### `CategoryFilter`
- Source: `frontend/src/components/products/CategoryFilter.jsx`
- Category: basic
- Description: Responsive category pill filter with counts and category color variants.
- Extractable props: `value`, `onChange`, `productCounts`.
- Hardcoded: product category definitions, icon map, active/inactive colors.

### `WarrantyBadge`
- Source: `frontend/src/components/products/WarrantyBadge.jsx`
- Category: basic
- Description: Warranty status badge/dot/border based on purchase date and duration.
- Extractable props: `purchaseDate`, `warrantyMonths`, `compact`.
- Hardcoded: warranty labels, icons, status colors, and 30-day expiring threshold.

### `ProductSelector`
- Source: `frontend/src/components/products/ProductSelector.jsx`
- Category: basic
- Description: Searchable product selection modal or dropdown with keyboard navigation.
- Extractable props: `open`, `onClose`, `onSelect`, `selectedId`, `mode`, `showWarrantyFilter`, `filterWarranty`, `placeholder`, `multiple`, `selectedIds`.
- Hardcoded: filter labels, keyboard hints, modal title, and layout classes.
