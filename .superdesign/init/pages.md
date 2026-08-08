# Pages & Dependencies

## / (Root Redirect)
Entry: `src/App.jsx`
Dependencies:
- `react-router-dom` (BrowserRouter, Routes, Route, Navigate)
- `src/components/auth/Login.jsx`
- `src/components/auth/Signup.jsx`
- `src/components/auth/forgot-password.jsx`

## /login (Login Page)
Entry: `src/components/auth/Login.jsx`
Dependencies:
- `react` (useState)
- `react-router-dom` (Link)
- `lucide-react` (Cpu, MessageSquare, Sparkles)

## /signup (Signup Page)
Entry: `src/components/auth/Signup.jsx`
Dependencies:
- `react` (useState)
- `react-router-dom` (Link)
- `lucide-react` (Cpu, MessageSquare, Bot)

## /forgot-password (Forgot Password Page)
Entry: `src/components/auth/forgot-password.jsx`
Dependencies:
- `react` (useState)
- `react-router-dom` (Link)
- `lucide-react` (Cpu, Lock, MessageSquare, Sparkles)