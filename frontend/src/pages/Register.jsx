import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ArrowRight, AlertCircle, HelpCircle } from 'lucide-react'

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
    </svg>
  )
}

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', password2: '', fpl_team_id: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
    if (form.password !== form.password2) {
      setError("Passwords don't match.")
      return
    }
    setLoading(true); setError('')
    try {
      const payload = { ...form }
      if (!payload.fpl_team_id) delete payload.fpl_team_id
      await register(payload)
      navigate('/dashboard')
    } catch (err) {
      const d = err.response?.data
      setError(typeof d === 'object' ? Object.values(d).flat().join(' ') : 'Registration failed.')
    } finally { setLoading(false) }
  }

  const inputStyle = {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: 'white',
  }

  const fields = [
    { key: 'email',      label: 'Email address',          type: 'email',    ph: 'you@example.com',  required: true  },
    { key: 'username',   label: 'Username',               type: 'text',     ph: 'fpl_wizard',       required: true  },
    { key: 'password',   label: 'Password',               type: 'password', ph: '8+ characters',    required: true  },
    { key: 'password2',  label: 'Confirm password',       type: 'password', ph: '••••••••',         required: true  },
    { key: 'fpl_team_id',label: 'FPL Team ID (optional)', type: 'number',   ph: '1234567',          required: false, hint: true },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden"
      style={{ background: '#0d001a', fontFamily: 'Inter, sans-serif' }}>

      {/* Ambient glows */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-15%] left-[-5%] w-[55%] h-[55%] rounded-full blur-[180px]"
          style={{ background: 'radial-gradient(ellipse, rgba(55,0,60,0.45) 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] rounded-full blur-[140px]"
          style={{ background: 'radial-gradient(ellipse, rgba(0,255,135,0.06) 0%, transparent 70%)' }} />
      </div>

      <div className="relative z-10 w-full max-w-md">

        {/* Logo */}
        <div className="flex items-center gap-3 justify-center mb-8">
          <FootballLogo size={36} />
          <span className="font-display font-bold text-white text-xl tracking-wide">
            FPL <span style={{ color: '#00ff87' }}>Scout</span>
          </span>
        </div>

        {/* Card */}
        <div className="rounded-2xl p-8"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,255,135,0.12)' }}>

          <div className="mb-6">
            <div className="inline-block gw-chip mb-4">FREE · NO CREDIT CARD</div>
            <h1 className="font-display font-bold text-white text-3xl mb-1">Create your account</h1>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Join FPL Scout and get your first AI picks this gameweek.
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg mb-5 text-sm"
              style={{ background: 'rgba(233,0,82,0.1)', border: '1px solid rgba(233,0,82,0.25)', color: '#e90052' }}>
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={submit} className="space-y-3.5">
            {fields.map(({ key, label, type, ph, required, hint }) => (
              <div key={key}>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <label className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.6)' }}>
                    {label}
                  </label>
                  {hint && (
                    <span className="text-xs px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(0,255,135,0.1)', color: '#00ff87' }}>
                      optional
                    </span>
                  )}
                </div>
                <input
                  type={type}
                  className="w-full rounded-lg px-4 py-3 text-sm transition-all outline-none"
                  style={inputStyle}
                  placeholder={ph}
                  value={form[key]}
                  onChange={set(key)}
                  required={required}
                  min={key === 'fpl_team_id' ? 1 : undefined}
                  onFocus={e => e.target.style.borderColor = 'rgba(0,255,135,0.5)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
                {key === 'fpl_team_id' && (
                  <p className="mt-1 text-xs flex items-center gap-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    <HelpCircle className="w-3 h-3" />
                    Find your ID on the FPL website under Points → your team name in the URL
                  </p>
                )}
              </div>
            ))}

            <button
              type="submit" disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3.5 rounded-lg font-bold text-sm transition-all group glow-green disabled:opacity-60 disabled:cursor-not-allowed mt-5"
              style={{ background: '#00ff87', color: '#0d001a' }}
            >
              {loading ? 'Creating account…' : (
                <>
                  Create Free Account
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <p className="text-center mt-5 text-sm" style={{ color: 'rgba(255,255,255,0.35)' }}>
            Already have an account?{' '}
            <Link to="/login" className="font-semibold" style={{ color: '#00ff87' }}>
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center mt-5">
          <Link to="/" className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>← Back to home</Link>
        </p>
      </div>
    </div>
  )
}
