# Shared UI Components

## Auth Components

### Login Component
- **File**: `src/components/auth/Login.jsx`
- **Description**: Login form with email/password fields, remember me checkbox, and Google OAuth button
- **Key Props**: None (self-contained)
- **Source Code**:
```jsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Cpu, MessageSquare, Sparkles } from 'lucide-react'

function Login() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  const [errors, setErrors] = useState({})

  const handleSubmit = (e) => {
    e.preventDefault()
    const validationErrors = validateForm()
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
    if (errors[name]) {
      setErrors(prev => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    }
  }

  function validateForm() {
    const errs = {}
    if (!formData.email.trim()) {
      errs.email = 'Email is required.'
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errs.email = 'Email is invalid.'
    }
    if (!formData.password) errs.password = 'Password is required.'
    return errs
  }

  return (
    <div className="min-h-screen bg-white flex">
      <div className="hidden lg:flex w-1/2 brand-gradient flex-col items-center justify-center p-16 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full -mr-48 -mt-48"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/5 rounded-full -ml-32 -mb-32"></div>
        
        <div className="relative z-10 w-full max-w-lg">
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 mb-12 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-3 h-3 rounded-full bg-red-400/80"></div>
              <div className="w-3 h-3 rounded-full bg-amber-400/80"></div>
              <div className="w-3 h-3 rounded-full bg-teal-400/80"></div>
            </div>
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex-shrink-0 flex items-center justify-center">
                  <MessageSquare className="text-white w-5 h-5" />
                </div>
                <div className="flex-1 bg-white/5 rounded-xl p-4">
                  <div className="h-2 w-24 bg-white/30 rounded mb-2"></div>
                  <div className="h-2 w-full bg-white/20 rounded mb-1"></div>
                  <div className="h-2 w-3/4 bg-white/20 rounded"></div>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-teal-500/20 flex-shrink-0 flex items-center justify-center">
                  <Sparkles className="text-white w-5 h-5" />
                </div>
                <div className="flex-1 bg-white/10 rounded-xl p-4">
                  <div className="h-2 w-32 bg-white/40 rounded mb-2"></div>
                  <div className="h-2 w-full bg-white/30 rounded mb-1"></div>
                  <div className="h-2 w-5/6 bg-white/30 rounded"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="text-center px-4">
            <h2 className="text-3xl font-bold text-white mb-4">The next generation of customer support</h2>
            <p className="text-blue-100 text-lg">
              Harness the power of AI to resolve tickets 10x faster and delight your customers at every touchpoint.
            </p>
          </div>

          <div className="mt-12 flex justify-center gap-8">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">99.9%</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">Uptime</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">500k+</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">Tickets resolved</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">4.9/5</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">CSAT Score</div>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 md:p-16 xl:p-24">
        <div className="w-full max-w-[440px]">
          <div className="mb-12 flex items-center gap-2">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
              <Cpu className="text-white w-6 h-6" />
            </div>
            <span className="text-xl font-bold text-slate-900 tracking-tight">3LM Solutions</span>
          </div>

          <div className="mb-10">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Welcome back</h1>
            <p className="text-slate-500">Please enter your details to access your dashboard.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="name@company.com"
                className={`w-full px-4 py-2.5 bg-white rounded-lg text-slate-900 placeholder:text-slate-400 input-focus ${errors.email ? 'border-red-500' : 'border-slate-200'}`}
              />
              {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email}</p>}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                  Password
                </label>
                <Link to="/forgot-password" className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors">
                  Forgot password?
                </Link>
              </div>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••"
                className={`w-full px-4 py-2.5 bg-white rounded-lg text-slate-900 placeholder:text-slate-400 input-focus ${errors.password ? 'border-red-500' : 'border-slate-200'}`}
              />
              {errors.password && <p className="text-red-500 text-sm mt-1">{errors.password}</p>}
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="remember-me"
                name="rememberMe"
                checked={formData.rememberMe}
                onChange={handleChange}
                className="h-4 w-4 text-blue-600 border-slate-300 rounded focus:ring-blue-600 transition-all"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-600 cursor-pointer">
                Remember me for 30 days
              </label>
            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white font-medium py-2.5 rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-600/20 transition-all shadow-sm"
            >
              Sign in to Dashboard
            </button>

            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-slate-400">Or continue with</span>
              </div>
            </div>

            <button
              type="button"
              className="w-full flex items-center justify-center gap-2 bg-white border border-slate-200 text-slate-600 font-medium py-2.5 rounded-lg hover:bg-slate-50 transition-all"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Login with google
            </button>
          </form>

          <p className="mt-10 text-center text-sm text-slate-500">
            Don't have an account?{' '}
            <Link to="/signup" className="font-medium text-blue-600 hover:text-blue-700 transition-colors ml-1">
              Sign up for a free trial
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login
```

### Signup Component
- **File**: `src/components/auth/Signup.jsx`
- **Description**: Registration form with full name, company name, email, password, and terms acceptance
- **Key Props**: None (self-contained)
- **Source Code**:
```jsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Cpu, MessageSquare, Bot } from 'lucide-react'

function Signup() {
  const [formData, setFormData] = useState({
    fullName: '',
    companyName: '',
    email: '',
    password: '',
    confirmPassword: '',
    terms: false
  })

  const [errors, setErrors] = useState({})

  function validateForm() {
    const errs = {}
    if (!formData.fullName.trim()) errs.fullName = 'Full Name is required.'
    if (!formData.companyName.trim()) errs.companyName = 'Company Name is required.'
    if (!formData.email.trim()) {
      errs.email = 'Email is required.'
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errs.email = 'Email is invalid.'
    }
    if (!formData.password) errs.password = 'Password is required.'
    if (formData.password !== formData.confirmPassword) errs.confirmPassword = 'Passwords do not match.'
    if (!formData.terms) errs.terms = 'You must agree to the Terms of Service and Privacy Policy.'
    return errs
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const validationErrors = validateForm()
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
    if (errors[name]) {
      setErrors(prev => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    }
  }

  return (
    <div className="min-h-screen flex bg-white">
      <div className="hidden lg:flex flex-1 brand-gradient relative overflow-hidden items-center justify-center p-12">
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full blur-3xl -mr-24 -mt-24"></div>
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-blue-400/10 rounded-full blur-3xl -ml-24 -mb-24"></div>
        
        <div className="relative z-10 max-w-lg text-center">
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-8 mb-12 shadow-2xl">
            <div className="flex gap-4 mb-6">
              <div className="w-8 h-2 bg-blue-400/40 rounded-full"></div>
              <div className="w-12 h-2 bg-white/20 rounded-full"></div>
              <div className="w-6 h-2 bg-white/20 rounded-full"></div>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <MessageSquare className="text-blue-300 w-5 h-5" />
                </div>
                <div className="flex-1 h-3 bg-white/10 rounded-full"></div>
                <div className="w-12 h-3 bg-white/5 rounded-full"></div>
              </div>
              <div className="flex items-center gap-3 flex-row-reverse">
                <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
                  <Bot className="text-white/80 w-5 h-5" />
                </div>
                <div className="flex-1 h-3 bg-blue-500/30 rounded-full"></div>
                <div className="w-16 h-3 bg-white/5 rounded-full"></div>
              </div>
            </div>

            <div className="mt-8 grid grid-cols-3 gap-3">
              <div className="h-16 bg-white/5 rounded-xl border border-white/10"></div>
              <div className="h-16 bg-blue-500/20 rounded-xl border border-white/20"></div>
              <div className="h-16 bg-white/5 rounded-xl border border-white/10"></div>
            </div>
          </div>

          <h2 className="text-4xl font-bold text-white mb-6 leading-tight">
            Empower your team with autonomous AI support
          </h2>
          <p className="text-blue-100 text-lg">
            3LM Solutions resolves 70% of common queries instantly, letting your agents focus on what matters most.
          </p>

          <div className="mt-16 text-left inline-flex items-center gap-4 bg-black/10 p-4 rounded-xl border border-white/5">
            <div className="w-12 h-12 rounded-full bg-slate-300 overflow-hidden">
              <img 
                src="https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah" 
                alt="Sarah Avatar" 
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <p className="text-white text-sm font-medium">"Halved our response times in weeks."</p>
              <p className="text-blue-300 text-xs">Sarah Chen, VP of Support @ GlobalTech</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-24 xl:px-32 py-12">
        <div className="max-w-md w-full mx-auto">
          <div className="mb-10">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
                <Cpu className="text-white w-6 h-6" />
              </div>
              <span className="text-2xl font-bold text-slate-900 tracking-tight">3LM Solutions</span>
            </div>
          </div>

          <header className="mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Create your account</h1>
            <p className="text-slate-600">Start scaling your customer support with enterprise AI.</p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-slate-700 mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                id="fullName"
                name="fullName"
                value={formData.fullName}
                onChange={handleChange}
                placeholder="Full Name"
                className={`w-full px-4 py-2.5 rounded-lg text-slate-900 placeholder:text-slate-400 input-focus transition-all ${errors.fullName ? 'border-red-500' : 'border-slate-200'}`}
              />
              {errors.fullName && <p className="text-red-500 text-sm mt-1">{errors.fullName}</p>}
            </div>

            <div>
              <label htmlFor="companyName" className="block text-sm font-medium text-slate-700 mb-1.5">
                Company Name
              </label>
              <input
                type="text"
                id="companyName"
                name="companyName"
                value={formData.companyName}
                onChange={handleChange}
                placeholder="Acme Corp"
                className={`w-full px-4 py-2.5 rounded-lg text-slate-900 placeholder:text-slate-400 input-focus transition-all ${errors.companyName ? 'border-red-500' : 'border-slate-200'}`}
              />
              {errors.companyName && <p className="text-red-500 text-sm mt-1">{errors.companyName}</p>}
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                Work Email
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="name@company.com"
                className={`w-full px-4 py-2.5 rounded-lg text-slate-900 placeholder:text-slate-400 input-focus transition-all ${errors.email ? 'border-red-500' : 'border-slate-200'}`}
              />
              {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email}</p>}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className={`w-full px-4 py-2.5 rounded-lg text-slate-900 placeholder:text-slate-400 input-focus transition-all ${errors.password ? 'border-red-500' : 'border-slate-200'}`}
                />
                {errors.password && <p className="text-red-500 text-sm mt-1">{errors.password}</p>}
              </div>
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 mb-1.5">
                  Confirm Password
                </label>
                <input
                  type="password"
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className={`w-full px-4 py-2.5 rounded-lg text-slate-900 placeholder:text-slate-400 input-focus transition-all ${errors.confirmPassword ? 'border-red-500' : 'border-slate-200'}`}
                />
                {errors.confirmPassword && <p className="text-red-500 text-sm mt-1">{errors.confirmPassword}</p>}
              </div>
            </div>

            <div className="flex items-start gap-3 py-2">
              <div className="flex items-center h-5">
                <input
                  id="terms"
                  type="checkbox"
                  name="terms"
                  checked={formData.terms}
                  onChange={handleChange}
                  className={`w-4 h-4 text-blue-600 rounded focus:ring-blue-500 ${errors.terms ? 'border-red-500' : 'border-slate-300'}`}
                />
              </div>
              <label htmlFor="terms" className="text-sm text-slate-500 leading-tight">
                I agree to the{' '}
                <Link to="/terms" className="text-blue-600 hover:underline font-medium">
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link to="/privacy" className="text-blue-600 hover:underline font-medium">
                  Privacy Policy
                </Link>.
              </label>
            </div>
            {errors.terms && <p className="text-red-500 text-sm">{errors.terms}</p>}

            <button
              type="submit"
              className="w-full bg-blue-600 text-white font-medium py-3 rounded-lg hover:bg-blue-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Create free account
            </button>
          </form>

          <div className="mt-8 pt-8 border-t border-slate-100 text-center">
            <p className="text-sm text-slate-600">
              Already have an account?{' '}
              <Link to="/login" className="text-blue-600 font-semibold hover:underline">
                Log in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Signup
```

### ForgotPassword Component
- **File**: `src/components/auth/forgot-password.jsx`
- **Description**: Password reset form with email input and success state
- **Key Props**: None (self-contained)
- **Source Code**:
```jsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Cpu, Lock, MessageSquare, Sparkles } from 'lucide-react'

function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [errors, setErrors] = useState({})
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    const validationErrors = {}
    if (!email.trim()) {
      validationErrors.email = 'Email is required.'
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      validationErrors.email = 'Email is invalid.'
    }
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return
    
    setSubmitted(true)
  }

  return (
    <div className="min-h-screen bg-white flex">
      <div className="hidden lg:flex w-1/2 brand-gradient flex-col items-center justify-center p-16 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full -mr-48 -mt-48"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/5 rounded-full -ml-32 -mb-32"></div>
        
        <div className="relative z-10 w-full max-w-lg">
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 mb-12 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-3 h-3 rounded-full bg-red-400/80"></div>
              <div className="w-3 h-3 rounded-full bg-amber-400/80"></div>
              <div className="w-3 h-3 rounded-full bg-teal-400/80"></div>
            </div>
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex-shrink-0 flex items-center justify-center">
                  <MessageSquare className="text-white w-5 h-5" />
                </div>
                <div className="flex-1 bg-white/5 rounded-xl p-4">
                  <div className="h-2 w-24 bg-white/30 rounded mb-2"></div>
                  <div className="h-2 w-full bg-white/20 rounded mb-1"></div>
                  <div className="h-2 w-3/4 bg-white/20 rounded"></div>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-teal-500/20 flex-shrink-0 flex items-center justify-center">
                  <Sparkles className="text-white w-5 h-5" />
                </div>
                <div className="flex-1 bg-white/10 rounded-xl p-4">
                  <div className="h-2 w-32 bg-white/40 rounded mb-2"></div>
                  <div className="h-2 w-full bg-white/30 rounded mb-1"></div>
                  <div className="h-2 w-5/6 bg-white/30 rounded"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="text-center px-4">
            <h2 className="text-3xl font-bold text-white mb-4">The next generation of customer support</h2>
            <p className="text-blue-100 text-lg">
              Harness the power of AI to resolve tickets 10x faster and delight your customers at every touchpoint.
            </p>
          </div>

          <div className="mt-12 flex justify-center gap-8">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">99.9%</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">Uptime</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">500k+</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">Tickets resolved</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">4.9/5</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">CSAT Score</div>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 md:p-16 xl:p-24">
        <div className="w-full max-w-[440px]">
          <div className="mb-12 flex items-center gap-2">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
              <Cpu className="text-white w-6 h-6" />
            </div>
            <span className="text-xl font-bold text-slate-900 tracking-tight">3LM Solutions</span>
          </div>

          <div className="mb-10">
            <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mb-6">
              <Lock className="text-slate-600 w-6 h-6" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Reset password</h1>
            <p className="text-slate-500">Enter the email address associated with your account and we'll send you a link to reset your password.</p>
          </div>

          {submitted ? (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 text-center">
              <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Check your email</h3>
              <p className="text-slate-500 text-sm">
                We've sent a password reset link to <strong>{email}</strong>. Please check your inbox and follow the instructions.
              </p>
              <button 
                onClick={() => setSubmitted(false)}
                className="mt-6 text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                Didn't receive the email? Try again
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (errors.email) setErrors({})
                  }}
                  placeholder="name@company.com"
                  className={`w-full px-4 py-2.5 bg-white rounded-lg text-slate-900 placeholder:text-slate-400 input-focus ${errors.email ? 'border-red-500' : 'border-slate-200'}`}
                />
                {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email}</p>}
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 text-white font-medium py-2.5 rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-600/20 transition-all shadow-sm"
              >
                Send reset link
              </button>
            </form>
          )}

          <p className="mt-10 text-center text-sm text-slate-500">
            Remember your password?{' '}
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-700 transition-colors ml-1">
              Back to sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default ForgotPassword
```