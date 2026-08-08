# Design System - Nexus AI Customer Support

## Product Context

Nexus AI is an enterprise-grade AI customer support platform. The application provides:
- Dashboard with real-time metrics
- Ticket management system
- AI chat assistant
- Knowledge base management
- Analytics and reporting
- User management

## Brand Identity

- **Primary Color**: Blue (#2563EB / blue-600)
- **Secondary Colors**: Slate (#0F172A for text, #64748B for muted text)
- **Accent Colors**: Teal (#0D9488), Amber (#F59E0B), Red (#EF4444)
- **Background**: #F8FAFC (slate-50)
- **Surface**: White (#FFFFFF)
- **Border**: #E2E8F0 (slate-200)

## Typography

- **Font Family**: Inter (Google Fonts)
- **Font Weights**: 300, 400, 500, 600, 700
- **Headings**: Bold (700), slate-900
- **Body**: Regular (400), slate-600
- **Muted**: slate-400, slate-500

## Spacing Scale

- Uses Tailwind CSS default spacing scale
- Base unit: 4px
- Common values: p-4 (16px), p-6 (24px), p-8 (32px), gap-6 (24px), gap-8 (32px)

## Border Radius

- Cards/Containers: rounded-xl (12px)
- Buttons: rounded-lg (8px)
- Badges: rounded-full
- Inputs: rounded-lg (8px)

## Shadows

- Custom shadow: `box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)`
- Card hover: translateY(-2px) with transition

## Layout

- Sidebar width: 260px (fixed)
- Main content: flex-1 with max-width 1440px
- Grid system: CSS Grid with Tailwind classes
- Responsive breakpoints: Tailwind defaults (md: 768px, lg: 1024px, xl: 1280px)

## Components

### Buttons
- Primary: bg-blue-600 text-white hover:bg-blue-700
- Secondary: bg-white border border-slate-200 text-slate-600 hover:bg-slate-50
- Padding: px-4 py-2
- Font: text-sm font-medium

### Cards
- Background: bg-white
- Border: border border-slate-200
- Shadow: custom-shadow
- Padding: p-6

### Status Badges
- Open: bg-blue-100 text-blue-600
- Pending: bg-orange-100 text-orange-600
- Resolved: bg-teal-100 text-teal-600
- High Priority: text-red-500
- Medium Priority: text-slate-500
- Low Priority: text-slate-400

### Navigation
- Left Sidebar: Dark (bg-slate-900) or Light (bg-white)
- Top Nav: White background with border-b
- Active state: bg-blue-600/10 text-blue-600

### Tables
- Header: bg-slate-50, uppercase, text-[10px], font-bold
- Rows: divide-y divide-slate-100
- Hover: hover:bg-slate-50

## Icons

- Icon Library: Lucide Icons (via iconify-icon CDN)
- Icon size: w-4 h-4 (16px) for inline, w-5 h-5 (20px) for navigation
- Icon color: inherits text color

## Motion/Animation

- Hover transitions: transition-colors (150ms)
- Card hover: transform translateY(-2px) with 300ms ease
- Loading states: Not yet defined

## Dark Mode

- Not implemented yet
- Current design is light mode only

## Responsive Design

- Mobile-first approach
- Sidebar collapses on mobile (to be implemented)
- Grid adjusts from 1 to 2 to 4 columns based on breakpoint