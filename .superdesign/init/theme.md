# Theme & Design Tokens

## CSS Variables

```css
:root {
  --primary: #2563EB;
  --primary-dark: #1E40AF;
  --text-primary: #0F172A;
  --text-secondary: #64748B;
  --background: #F8FAFC;
  --surface: #FFFFFF;
  --border: #E2E8F0;
}
```

## Global Styles

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
@import "tailwindcss";

body {
  font-family: 'Inter', sans-serif;
  background-color: var(--background);
  color: var(--text-primary);
}

.brand-gradient {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
}

.input-focus {
  transition: all 0.2s ease;
}

.input-focus:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.custom-shadow {
  box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1);
}
```

## Tailwind Configuration

### Vite Config
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

### Color Palette (from CSS variables and Tailwind)
- **Primary**: Blue 600 (#2563EB)
- **Primary Dark**: Blue 800 (#1E40AF)
- **Background**: Slate 50 (#F8FAFC)
- **Surface**: White (#FFFFFF)
- **Text Primary**: Slate 900 (#0F172A)
- **Text Secondary**: Slate 500 (#64748B)
- **Border**: Slate 200 (#E2E8F0)

### Typography
- **Font Family**: Inter (Google Fonts)
- **Font Weights**: 300, 400, 500, 600, 700

### Components
- **Input Focus**: Blue ring with opacity
- **Brand Gradient**: 135deg linear gradient from primary to primary-dark
- **Custom Shadow**: Subtle shadow for elevation