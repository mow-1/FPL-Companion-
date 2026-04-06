import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', password2: '', fpl_team_id: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
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

  return (
    <div className="relative min-h-screen bg-slate-100 dark:bg-[#0B0F19] flex items-center justify-center p-4 overflow-hidden">
      {/* Ambient background */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-900/20 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/20 blur-[120px]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px]" />
      </div>
      <div className="relative z-10 bg-slate-100 dark:bg-white/80 dark:bg-[#0f172a]/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-2xl p-8 w-full max-w-md shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Create Account</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Join <span className="text-cyan-400">FPL</span> Assistant</p>
        </div>
        {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-3 mb-4 text-sm">{error}</div>}
        <form onSubmit={submit} className="space-y-4">
          {[
            { key: 'email', label: 'Email', type: 'email', ph: 'you@example.com' },
            { key: 'username', label: 'Username', type: 'text', ph: 'fpl_wizard' },
            { key: 'password', label: 'Password', type: 'password', ph: '••••••••' },
            { key: 'password2', label: 'Confirm Password', type: 'password', ph: '••••••••' },
            { key: 'fpl_team_id', label: 'FPL Team ID (optional)', type: 'number', ph: '1234567' },
          ].map(({ key, label, type, ph }) => (
            <div key={key}>
              <label className="text-slate-500 dark:text-slate-400 text-sm mb-1 block">{label}</label>
              <input
                type={type}
                className="w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-4 py-3 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
                placeholder={ph}
                value={form[key]}
                onChange={set(key)}
                required={key !== 'fpl_team_id'}
              />
            </div>
          ))}
          <button type="submit" disabled={loading}
            className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-900 dark:text-white font-semibold rounded-lg py-3 transition-colors">
            {loading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>
        <p className="text-center text-slate-500 dark:text-slate-400 mt-6 text-sm">
          Already have an account?{' '}
          <Link to="/login" className="text-cyan-400 hover:text-cyan-300 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
