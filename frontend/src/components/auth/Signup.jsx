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
            Centralisez vos demandes de support et connectez vos équipes à vos données métier.
          </p>
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
