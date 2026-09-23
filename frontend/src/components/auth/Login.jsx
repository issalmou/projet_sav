import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Cpu, MessageSquare, Sparkles, Loader2 } from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { homeFor, resolveRole } from '../../contexts/roles'
import { getCurrentUserRequest, loginRequest } from '../../api/auth'
import { useI18n } from '../../i18n/useI18n'

function Login() {
  const { login } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
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

      // En mode backend, le profil est chargé séparément après le token.
      if (data.access_token) {
        const profile = await getCurrentUserRequest(data.access_token).catch(() => null)
        if (profile) {
          data = { ...data, ...profile, name: profile.full_name || data.name || '' }
        }
      }
    } catch (err) {
      setErrors({ form: err.message || t('auth.failed') })
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
      errs.email = t('auth.emailRequired')
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errs.email = t('auth.emailInvalid')
    }
    if (!formData.password) {
      errs.password = t('auth.passwordRequired')
    } else if (formData.password.length < 8) {
      errs.password = t('auth.passwordMin')
    }
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
            <h2 className="text-3xl font-bold text-white mb-4">{t('auth.heroTitle')}</h2>
            <p className="text-blue-100 text-lg">
              {t('auth.heroText')}
            </p>
          </div>

          <div className="mt-12 flex justify-center gap-8">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">99.9%</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">{t('auth.uptime')}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">500k+</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">{t('auth.ticketsResolved')}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">4.9/5</div>
              <div className="text-xs uppercase tracking-widest text-blue-200/60 font-semibold">{t('auth.csat')}</div>
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
             <h1 className="text-3xl font-bold text-slate-900 mb-2">{t('auth.welcomeBack')}</h1>
             <p className="text-slate-500">{t('auth.enterDetails')}</p>
           </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {errors.form && (
              <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
                {errors.form}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('auth.email')}
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
                  {t('auth.password')}
                </label>
                <Link to="/forgot-password" className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors">
                  {t('auth.forgot')}
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

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white font-medium py-2.5 rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-600/20 transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('auth.signing')}
                </>
              ) : (
                t('auth.signin')
              )}
            </button>

           </form>
        </div>
      </div>
    </div>
  )
}

export default Login
