import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Cpu, MessageSquare, Sparkles, Loader2 } from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { homeFor, resolveRole } from '../../contexts/roles'
import { getCurrentUserRequest, loginRequest } from '../../api/auth'

function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const validationErrors = validateForm()
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return

    setLoading(true)
    setErrors({})

    let data
    try {
      data = await loginRequest({
        email: formData.email,
        password: formData.password,
      })

      // Le backend renvoie uniquement les tokens : on charge le profil courant
      // pour disposer du nom, de l'email et du rôle de l'utilisateur.
      if (data.access_token) {
        const profile = await getCurrentUserRequest(data.access_token).catch(() => null)
        if (profile) {
          data = { ...data, ...profile, name: profile.full_name || data.name || '' }
        }
      }
    } catch (err) {
      setErrors({ form: err.message || 'Authentification échouée.' })
      setLoading(false)
      return
    }

    // Le rôle provient exclusivement de la réponse de l'API (jamais du client).
    const role = resolveRole(data.role?.name || data.role || data.user?.role)
    const success = login({ ...data, role })

    setLoading(false)
    if (success) {
      navigate(homeFor({ role }), { replace: true })
    }
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
            {errors.form && (
              <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
                {errors.form}
              </div>
            )}

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
              disabled={loading}
              className="w-full bg-blue-600 text-white font-medium py-2.5 rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-600/20 transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connexion en cours...
                </>
              ) : (
                'Sign in to Dashboard'
              )}
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
