# SAV Frontend - Codebase Explanation

## Project Overview

This is a **React + Vite** dashboard application for **3LM Solutions** (branded as "Nexus AI"). It's a customer support portal (SAV = Service Après-Vente) where clients manage tickets, products, and interact with AI-powered support.

**Tech Stack:**
- React 19 (UI framework)
- Vite 8 (build tool)
- Tailwind CSS 4 (styling)
- React Router 7 (routing/navigation)
- Lucide React (icon library)

---

## How the App Starts

```
index.html  →  main.jsx  →  App.jsx
```

1. **`src/main.jsx`** - Entry point. Mounts `<App />` inside `<StrictMode>` to the DOM
2. **`src/App.jsx`** - Defines all routes. Two route groups:
   - **Auth routes** (`/login`, `/signup`, `/forgot-password`) - standalone pages, no sidebar
   - **Protected routes** (everything else) - wrapped in `<Layout />` which adds sidebar + navbar

---

## Routing Structure (App.jsx)

```
/                 → redirects to /login
/login            → Login page
/signup           → Signup page
/forgot-password  → ForgotPassword page

/dashboard        → Dashboard page (inside Layout)
/chat             → Coming Soon placeholder
/tickets           → Coming Soon placeholder
/products          → Coming Soon placeholder
/knowledge         → Coming Soon placeholder
/analytics         → Coming Soon placeholder
/notifications     → Coming Soon placeholder
/admin             → Coming Soon placeholder
/settings          → Coming Soon placeholder
*                 → redirects to /login
```

**Key pattern:** Routes inside `<Route element={<Layout />}>` use React Router's `<Outlet />` to render child pages inside the sidebar+navbar shell.

---

## Layout System

### `src/components/layout/Layout.jsx`
The main layout wrapper for all dashboard pages.

```
+------------------+------------------+
|                  |                  |
|   LeftSidebar    |   TopNavBar      |
|   (264px wide)   |   (64px tall)   |
|                  |                  |
|                  +------------------+
|                  |                  |
|                  |   <Outlet />     |
|                  |   (page content) |
|                  |                  |
+------------------+------------------+
```

- Uses `flex min-h-screen` for full-page layout
- `<LeftSidebar />` is fixed width (`w-64`)
- Right side uses `flex-1 flex flex-col min-w-0` to fill remaining space
- `<TopNavBar />` sits at the top
- `<Outlet />` renders whichever page matches the current route

### `src/components/layout/LeftSidebar.jsx`
Dark sidebar navigation with brand logo and menu.

- **Logo area:** "3LM Solutions" with a blue CPU icon
- **Navigation:** 9 menu items using `<NavLink>` which auto-detects the active route
- **Active state:** White background (`bg-white/10`) with a blue left border
- **Inactive state:** Gray text with hover effects
- **Footer:** "Deconnexion" (Logout) button
- Menu items are defined in a `menuItems` array for easy maintenance

### `src/components/layout/TopNavBar.jsx`
Top bar with search, notifications, and user profile.

- **Left side:** Search input field
- **Right side:** 
  - Notification bell with blue dot indicator
  - User avatar (initials "JD"), name "John Doe", role "Client Premium"
  - Dropdown chevron
- All props are configurable (userName, userRole, userInitials)

---

## Authentication Pages

All auth pages share the same visual pattern: **split-screen layout** - blue gradient on the left (with decorative mockups), white form on the right.

### `src/components/auth/Login.jsx`
- **State:** email, password, rememberMe (using `useState`)
- **Validation:** Checks for empty fields and valid email format
- **Error handling:** Shows red error messages under invalid fields, clears errors on re-type
- **Google login button** (UI only, not functional)
- Links to signup and forgot-password pages

### `src/components/auth/Signup.jsx`
- **State:** fullName, companyName, email, password, confirmPassword, terms
- **Validation:** All fields required, email format, password match, terms acceptance
- Same split-screen layout as Login

### `src/components/auth/forgot-password.jsx`
- **State:** email, errors, submitted (boolean for success state)
- **Two views:** 
  1. Email input form (before submission)
  2. "Check your email" success message (after submission)
- "Try again" button resets the submitted state

**Common pattern in all auth forms:**
```jsx
const [formData, setFormData] = useState({...})
const [errors, setErrors] = useState({})

const handleChange = (e) => {
  // Update form data
  // Clear error for this field when user types
}

const handleSubmit = (e) => {
  e.preventDefault()
  const validationErrors = validateForm()
  setErrors(validationErrors)
  if (Object.keys(validationErrors).length > 0) return
  // Proceed if valid
}
```

---

## Dashboard Page

### `src/pages/Dashboard.jsx`
The main landing page after login. Divided into sections:

**1. Welcome Header**
- Greeting: "Bonjour, John"
- "Nouveau Ticket" button (blue, top-right)

**2. Stats Grid (4 cards)**
Uses `<StatCard>` component:
| Card | Value | Color |
|------|-------|-------|
| Tickets Ouverts | 3 | blue |
| Messages | 12 | blue |
| Statut Systeme | Operationnel | teal |
| Services Actifs | 08 | indigo |

**3. Main Content (2/3 width)**
- **Activites Recentes** - List of 3 recent events (ticket resolved, system update, invoice ready)
- **Mes Produits a la une** - 2 featured product cards (monitor and gateway hub)

**4. Right Sidebar (1/3 width)**
- **Guide du Portail** - Blue banner with PDF download button
- **Aide & Documentation** - Knowledge base search with article links
- **Mon Parc Nexus** - Health monitor showing 100% system health

### `src/components/dashboard/StatCard.jsx`
Reusable stat card component.

**Props:**
- `title` - Card label
- `value` - Main number/text
- `subtitle` - Secondary text (shown when no trend)
- `trend` - Trend text (shown when no subtitle)
- `icon` - Icon name: "ticket", "message", "activity", "layers"
- `color` - Color scheme: "blue", "teal", "indigo", "orange"

**Logic:**
- Maps icon string to actual Lucide icon component via `iconMap`
- Maps color string to Tailwind classes via `colorMap`
- Shows either `trend` or `subtitle` (not both)

---

## Styling System

### `src/index.css`
Custom CSS variables and utility classes:
- **CSS Variables:** `--primary`, `--text-primary`, `--background`, etc.
- **`.brand-gradient`** - Blue gradient used on auth page left panels
- **`.input-focus`** - Focus ring effect for form inputs
- **`.custom-shadow`** - Subtle shadow for cards
- **`.card-hover`** - Lift effect on hover (translateY + shadow)
- **`.scrollbar-hide`** - Hides scrollbars on sidebar navigation

### Tailwind CSS
All styling is done via Tailwind utility classes directly in JSX. The project uses Tailwind v4 with the Vite plugin.

---

## File Structure

```
src/
├── main.jsx                          # App entry point
├── App.jsx                           # Router & routes
├── index.css                         # Global styles + Tailwind
├── components/
│   ├── auth/
│   │   ├── Login.jsx                 # Login form
│   │   ├── Signup.jsx                # Registration form
│   │   └── forgot-password.jsx       # Password reset form
│   ├── layout/
│   │   ├── Layout.jsx                # Main layout wrapper
│   │   ├── LeftSidebar.jsx           # Sidebar navigation
│   │   └── TopNavBar.jsx             # Top bar with search & profile
│   └── dashboard/
│       └── StatCard.jsx              # Reusable stat card
└── pages/
    └── Dashboard.jsx                 # Main dashboard page
```

---

## Key Concepts

### How Routing Works
React Router renders the route matching the URL. Routes nested under `<Route element={<Layout />}>` render inside Layout's `<Outlet />`. This means every dashboard page automatically gets the sidebar and navbar without repeating code.

### How Navigation Highlights Work
`<NavLink>` in the sidebar automatically sets `isActive` to true when the current URL matches its `to` prop. This toggles between active/inactive CSS classes.

### How Forms Handle Validation
Each auth form maintains its own `formData` and `errors` state. On submit, validation runs and populates `errors`. Fields clear their error when the user starts typing again. No external form library is used.

### How StatCard Reuses Code
The component accepts string keys for icon and color, then maps them to actual values internally. This makes the dashboard page cleaner since you only pass simple strings like `icon="ticket"` and `color="blue"`.

---

## What's Not Implemented Yet

The following pages are placeholders showing "Coming Soon":
- Chat AI
- Tickets
- Products
- Knowledge Base
- Analytics
- Notifications
- Administration
- Settings

The logout button in the sidebar is also non-functional (no click handler).
