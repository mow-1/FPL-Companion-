import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ArrowRight, AlertCircle } from 'lucide-react'

function FootballLogo({ size = 44 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <circle cx="20" cy="20" r="18" fill="#00ff87" opacity="0.12" />
      <circle cx="20" cy="20" r="16" stroke="#00ff87" strokeWidth="1.5" fill="none" />
      <polygon points="20,5 23.5,10 20,13.5 16.5,10" fill="#00ff87" />
      <polygon points="32,13 30,18.5 25.5,18 24,12.5" fill="#00ff87" opacity="0.75" />
      <polygon points="30,27 25.5,28 23.5,23 27,19.5" fill="#00ff87" opacity="0.75" />
      <polygon points="20,33 16.5,28 20,25.5 23.5,28" fill="#00ff87" opacity="0.75" />
      <polygon points="10,27 13,19.5 16.5,23 14.5,28" fill="#00ff87" opacity="0.5" />
      <polygon points="8,13 16,12.5 14.5,18 10,18.5" fill="#00ff87" opacity="0.5" />
      <polygon points="20,13.5 25.5,18 24,23 16.5,23 14.5,18 16.5,13.5"
        stroke="#00ff87" strokeWidth="0.8" fill="none" opacity="0.4" />
    </svg>
  )
}

/* Aerial pitch lines for left panel */
function PitchLines() {
  return (
    <svg viewBox="0 0 400 600" className="absolute inset-0 w-full h-full opacity-[0.08]" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="600" fill="none" />
      <rect x="20" y="20" width="360" height="560" stroke="white" strokeWidth="2" fill="none" />
      <line x1="200" y1="20" x2="200" y2="580" stroke="white" strokeWidth="1.5" />
      <circle cx="200" cy="300" r="80" stroke="white" strokeWidth="1.5" fill="none" />
      <circle cx="200" cy="300" r="3" fill="white" />
      <rect x="20" y="170" width="100" height="260" stroke="white" strokeWidth="1.5" fill="none" />
      <rect x="20" y="220" width="40" height="160" stroke="white" strokeWidth="1.5" fill="none" />
      <circle cx="80" cy="300" r="3" fill="white" />
      <path d="M 120 200 A 80 80 0 0 0 120 400" stroke="white" strokeWidth="1.5" fill="none" />
      <rect x="280" y="170" width="100" height="260" stroke="white" strokeWidth="1.5" fill="none" />
      <rect x="340" y="220" width="40" height="160" stroke="white" strokeWidth="1.5" fill="none" />
      <circle cx="320" cy="300" r="3" fill="white" />
      <path d="M 280 200 A 80 80 0 0 1 280 400" stroke="white" strokeWidth="1.5" fill="none" />
    </svg>
  )
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async e => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await login(form.email, form.password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check your email and password.')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#0d001a', fontFamily: 'Inter, sans-serif' }}>

      {/* Left panel — FPL branding */}
      <div className="hidden lg:flex flex-col justify-between w-[420px] flex-shrink-0 relative overflow-hidden p-10"
        style={{ background: 'linear-gradient(160deg, #37003c 0%, #1a0030 60%, #0d001a 100%)', borderRight: '1px solid rgba(0,255,135,0.1)' }}>
        <PitchLines />
        {/* Top — logo */}
        <div className="relative z-10 flex items-center gap-3">
          <FootballLogo size={36} />
          <span className="font-display font-bold text-white text-xl tracking-wide">
            FPL <span style={{ color: '#00ff87' }}>Scout</span>
          </span>
        </div>
        {/* Middle — tagline */}
        <div className="relative z-10">
          <div className="inline-block gw-chip mb-5">2025/26 SEASON</div>
          <h2 className="font-display font-bold text-white leading-tight mb-4"
            style={{ fontSize: '38px', letterSpacing: '-0.02em' }}>
            Your edge in<br />every gameweek.
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>
            AI predictions built on 10 seasons of Premier League data. Captain picks, transfer targets,
            and a best XI — every single gameweek.
          </p>
        </div>
        {/* Bottom — social proof */}
        <div className="relative z-10 space-y-3">
          {[
            { num: '9/10', label: 'Predictions within 2 pts' },
            { num: 'GW1→38', label: 'Full season coverage' },
            { num: '10 yrs', label: 'Of Premier League data' },
          ].map(s => (
            <div key={s.num} className="flex items-center gap-3">
              <span className="font-score font-bold text-lg" style={{ color: '#00ff87', minWidth: '70px' }}>{s.num}</span>
              <span className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6">

        {/* Ambient glow */}
        <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-[-15%] right-[-5%] w-[50%] h-[50%] rounded-full blur-[160px]"
            style={{ background: 'radial-gradient(ellipse, rgba(55,0,60,0.4) 0%, transparent 70%)' }} />
        </div>

        <div className="relative z-10 w-full max-w-md">

          {/* Mobile logo */}
          <div className="flex items-center gap-3 justify-center mb-8 lg:hidden">
            <FootballLogo size={32} />
            <span className="font-display font-bold text-white text-xl tracking-wide">
              FPL <span style={{ color: '#00ff87' }}>Scout</span>
            </span>
          </div>

          {/* Card */}
          <div className="rounded-2xl p-8"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,255,135,0.12)' }}>

            <div className="mb-8">
              <h1 className="font-display font-bold text-white text-3xl mb-1">Welcome back</h1>
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Sign in to your FPL Scout account</p>
            </div>

            {error && (
              <div className="flex items-start gap-2.5 p-3 rounded-lg mb-5 text-sm"
                style={{ background: 'rgba(233,0,82,0.1)', border: '1px solid rgba(233,0,82,0.25)', color: '#e90052' }}>
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  Email address
                </label>
                <input
                  type="email" required
                  className="w-full rounded-lg px-4 py-3 text-white text-sm transition-all outline-none"
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                  }}
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  onFocus={e => e.target.style.borderColor = 'rgba(0,255,135,0.5)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  Password
                </label>
                <input
                  type="password" required
                  className="w-full rounded-lg px-4 py-3 text-white text-sm transition-all outline-none"
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                  }}
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  onFocus={e => e.target.style.borderColor = 'rgba(0,255,135,0.5)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
              </div>
              <button
                type="submit" disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-3.5 rounded-lg font-bold text-sm transition-all group glow-green disabled:opacity-60 disabled:cursor-not-allowed"
                style={{ background: '#00ff87', color: '#0d001a' }}
              >
                {loading ? 'Signing in…' : (
                  <>
                    Sign In
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>
            </form>

            <p className="text-center mt-6 text-sm" style={{ color: 'rgba(255,255,255,0.35)' }}>
              Don't have an account?{' '}
              <Link to="/register" className="font-semibold transition-colors" style={{ color: '#00ff87' }}>
                Create one free
              </Link>
            </p>
          </div>

          <p className="text-center mt-6 text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>
            <Link to="/" style={{ color: 'rgba(255,255,255,0.25)' }}>← Back to home</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
