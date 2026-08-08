# Extractable Components

## Layout Components

### BrandLogo
- **Source**: `src/components/auth/Login.jsx` (lines 110-115)
- **Category**: layout
- **Description**: Company logo with icon and text
- **Extractable Props**: None (hardcoded)
- **Hardcoded**: Blue square with Cpu icon, "3LM Solutions" text

### GradientPanel
- **Source**: `src/components/auth/Login.jsx` (lines 49-106)
- **Category**: layout
- **Description**: Left panel with brand gradient and decorative elements
- **Extractable Props**: None (hardcoded)
- **Hardcoded**: Gradient background, decorative circles, stats display

## Basic Components

### FormInput
- **Source**: `src/components/auth/Login.jsx` (lines 127-136)
- **Category**: basic
- **Description**: Text input with label and error state
- **Extractable Props**: error (string), type (string)
- **Hardcoded**: Label styling, input classes, error text styling

### FormButton
- **Source**: `src/components/auth/Login.jsx` (lines 174-179)
- **Category**: basic
- **Description**: Primary action button with hover/focus states
- **Extractable Props**: None (hardcoded)
- **Hardcoded**: Blue background, white text, hover/focus states

### OAuthButton
- **Source**: `src/components/auth/Login.jsx` (lines 190-201)
- **Category**: basic
- **Description**: OAuth login button with provider icon
- **Extractable Props**: None (hardcoded)
- **Hardcoded**: Google SVG icon, white background, border styling

### CheckboxField
- **Source**: `src/components/auth/Login.jsx` (lines 160-172)
- **Category**: basic
- **Description**: Checkbox with label
- **Extractable Props**: None (hardcoded)
- **Hardcoded**: Checkbox styling, label text