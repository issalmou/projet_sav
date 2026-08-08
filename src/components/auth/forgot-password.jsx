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
