import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { updateProfile, changePassword, getFplManager } from '../api/fpl'
import { User, Shield, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'

const inputCls = 'w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-white text-sm focus:outline-none focus:border-cyan-500 focus:bg-slate-100 dark:bg-white/8 placeholder-slate-400 dark:placeholder-slate-500 transition-all'

function Section({ title, icon: Icon, iconColor = 'text-cyan-400', children }) {
  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-6 space-y-5">
      <div className="flex items-center gap-2.5">
        {Icon && <Icon className={`w-4 h-4 ${iconColor}`} />}
        <h3 className="font-semibold text-slate-900 dark:text-white text-sm uppercase tracking-wider">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</label>
      {hint && <p className="text-xs text-slate-600 dark:text-slate-500 leading-relaxed">{hint}</p>}
      {children}
    </div>
  )
}

export default function Profile() {
  const { user, setUser } = useAuth()
  const [form, setForm]     = useState({ username: '', fpl_team_id: '', fpl_team_name: '', bio: '', avatar: '' })
  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', new_password2: '' })
  const [saved, setSaved]   = useState(false)
  const [pwMsg, setPwMsg]   = useState(null)
  const [fplPreview, setFplPreview]   = useState(null)
  const [fplChecking, setFplChecking] = useState(false)

  useEffect(() => {
    if (user) {
      setForm({
        username:      user.username      || '',
        fpl_team_id:   user.fpl_team_id   || '',
        fpl_team_name: user.fpl_team_name || '',
        bio:           user.bio           || '',
        avatar:        user.avatar        || '',
      })
    }
  }, [user])

  const profileMut = useMutation({
    mutationFn: data => updateProfile(data),
    onSuccess: ({ data }) => {
      setUser(data)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const pwMut = useMutation({
    mutationFn: data => changePassword(data),
    onSuccess: () => {
      setPwMsg({ ok: true, text: 'Password changed successfully.' })
      setPwForm({ old_password: '', new_password: '', new_password2: '' })
      setTimeout(() => setPwMsg(null), 4000)
    },
    onError: err => {
      const d = err.response?.data
      setPwMsg({ ok: false, text: typeof d === 'object' ? Object.values(d).flat().join(' ') : 'Failed to change password.' })
    },
  })

  const set   = k => e => setForm(f => ({ ...f, [k]: e.target.value }))
  const setPw = k => e => setPwForm(f => ({ ...f, [k]: e.target.value }))

  const handleSave = e => {
    e.preventDefault()
    const payload = { ...form }
    if (!payload.fpl_team_id) delete payload.fpl_team_id
    profileMut.mutate(payload)
  }

  const handlePwSave = e => {
    e.preventDefault()
    pwMut.mutate(pwForm)
  }

  const lookupFplTeam = async () => {
    if (!form.fpl_team_id) return
    setFplChecking(true)
    setFplPreview(null)
    try {
      const { data } = await getFplManager(form.fpl_team_id)
      setFplPreview({ name: data.name, overall_rank: data.summary_overall_rank })
      setForm(f => ({ ...f, fpl_team_name: data.name }))
    } catch {
      setFplPreview({ error: 'Team not found. Check your FPL Team ID.' })
    } finally { setFplChecking(false) }
  }

  const initials = user?.username?.[0]?.toUpperCase() || '?'

  return (
    <div className="max-w-2xl space-y-6">
      {/* Page header */}
      <header>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
          <User className="w-7 h-7 text-cyan-400" />
          Profile
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Manage your account and FPL team connection.</p>
      </header>

      {/* Avatar card */}
      <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-6 flex items-center gap-5">
        <div className="relative flex-shrink-0">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center text-2xl font-bold text-slate-900 dark:text-white shadow-lg shadow-cyan-500/20">
            {initials}
          </div>
          <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 border-2 border-[#0B0F19] flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-white" />
          </div>
        </div>
        <div className="min-w-0">
          <p className="font-bold text-lg text-slate-900 dark:text-white truncate">{user?.username}</p>
          <p className="text-slate-500 dark:text-slate-400 text-sm truncate">{user?.email}</p>
          {user?.fpl_team_id ? (
            <p className="text-cyan-400 text-sm mt-1 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 flex-shrink-0" />
              Team #{user.fpl_team_id}{user.fpl_team_name ? ` · ${user.fpl_team_name}` : ''}
            </p>
          ) : (
            <p className="text-yellow-400 text-sm mt-1 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              No FPL Team ID — add it below to sync your squad
            </p>
          )}
        </div>
      </div>

      {/* Account details */}
      <form onSubmit={handleSave} className="space-y-4">
        <Section title="Account Details" icon={User}>
          <Field label="Username">
            <input className={inputCls} value={form.username} onChange={set('username')} placeholder="your_username" />
          </Field>
          <Field label="Bio">
            <textarea className={inputCls + ' resize-none'} rows={3} value={form.bio} onChange={set('bio')} placeholder="Tell us about yourself…" />
          </Field>
          <Field label="Avatar URL">
            <input className={inputCls} value={form.avatar} onChange={set('avatar')} placeholder="https://…" />
          </Field>
        </Section>

        <Section title="FPL Team" icon={ExternalLink} iconColor="text-emerald-400">
          <Field
            label="FPL Team ID"
            hint="Find your ID in the FPL app: Points → tap your team name → check the URL (entry/XXXXXXX/event/1)"
          >
            <div className="flex gap-2">
              <input
                className={inputCls}
                type="number"
                value={form.fpl_team_id}
                onChange={set('fpl_team_id')}
                placeholder="e.g. 1234567"
              />
              <button
                type="button"
                onClick={lookupFplTeam}
                disabled={!form.fpl_team_id || fplChecking}
                className="flex-shrink-0 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-slate-900 dark:text-white px-5 rounded-xl text-sm font-medium transition-colors"
              >
                {fplChecking ? '…' : 'Verify'}
              </button>
            </div>
            {fplPreview && !fplPreview.error && (
              <div className="mt-2 flex items-center gap-2 text-emerald-400 text-sm bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span className="font-medium">{fplPreview.name}</span>
                {fplPreview.overall_rank && (
                  <span className="text-slate-500 dark:text-slate-400 text-xs ml-auto">Rank #{fplPreview.overall_rank?.toLocaleString()}</span>
                )}
              </div>
            )}
            {fplPreview?.error && (
              <div className="mt-2 flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {fplPreview.error}
              </div>
            )}
          </Field>
          <Field label="Team Name">
            <input className={inputCls} value={form.fpl_team_name} onChange={set('fpl_team_name')} placeholder="Auto-filled when verified above" />
          </Field>
        </Section>

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={profileMut.isPending}
            className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-900 dark:text-white px-6 py-2.5 rounded-xl font-semibold text-sm transition-colors shadow-lg shadow-cyan-500/20"
          >
            {profileMut.isPending ? 'Saving…' : 'Save Changes'}
          </button>
          {saved && (
            <span className="flex items-center gap-1.5 text-emerald-400 text-sm font-medium">
              <CheckCircle className="w-4 h-4" /> Saved
            </span>
          )}
          {profileMut.isError && (
            <span className="text-red-400 text-sm">
              {Object.values(profileMut.error?.response?.data || {}).flat().join(' ') || 'Save failed.'}
            </span>
          )}
        </div>
      </form>

      {/* Change password */}
      <form onSubmit={handlePwSave}>
        <Section title="Change Password" icon={Shield} iconColor="text-purple-400">
          {[
            { key: 'old_password',  label: 'Current Password'  },
            { key: 'new_password',  label: 'New Password'       },
            { key: 'new_password2', label: 'Confirm New Password' },
          ].map(({ key, label }) => (
            <Field key={key} label={label}>
              <input
                className={inputCls}
                type="password"
                value={pwForm[key]}
                onChange={setPw(key)}
                placeholder="••••••••"
                required
              />
            </Field>
          ))}
          <div className="flex items-center gap-4 pt-1">
            <button
              type="submit"
              disabled={pwMut.isPending}
              className="bg-slate-100 dark:bg-white/8 hover:bg-slate-100 dark:hover:bg-slate-200 dark:bg-white/15 border border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-slate-300 dark:border-white/20 disabled:opacity-50 text-slate-900 dark:text-white px-6 py-2.5 rounded-xl font-semibold text-sm transition-colors"
            >
              {pwMut.isPending ? 'Updating…' : 'Update Password'}
            </button>
            {pwMsg && (
              <span className={`flex items-center gap-1.5 text-sm font-medium ${pwMsg.ok ? 'text-emerald-400' : 'text-red-400'}`}>
                {pwMsg.ok ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                {pwMsg.text}
              </span>
            )}
          </div>
        </Section>
      </form>
    </div>
  )
}
