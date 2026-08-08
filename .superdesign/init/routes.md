# Routes Configuration

## Router Setup

### File-based Configuration
- **Router Type**: React Router DOM v7
- **Config File**: `src/App.jsx`

### Route Table

| URL Path | Component | Description |
|----------|-----------|-------------|
| `/` | `Navigate to /login` | Root redirect to login |
| `/login` | `Login` | User authentication page |
| `/signup` | `Signup` | New account registration |
| `/forgot-password` | `ForgotPassword` | Password reset request |

### Route Details

#### `/login` (Login Page)
- **Component**: `src/components/auth/Login.jsx`
- **Description**: Login form with email/password fields, remember me checkbox, and Google OAuth
- **Features**:
  - Email validation
  - Password validation
  - Remember me functionality
  - Google login integration
  - Link to signup and forgot password

#### `/signup` (Signup Page)
- **Component**: `src/components/auth/Signup.jsx`
- **Description**: Registration form for new users
- **Features**:
  - Full name input
  - Company name input
  - Email validation
  - Password confirmation
  - Terms of service acceptance

#### `/forgot-password` (Forgot Password Page)
- **Component**: `src/components/auth/forgot-password.jsx`
- **Description**: Password reset request form
- **Features**:
  - Email input
  - Success state with confirmation message
  - Retry option