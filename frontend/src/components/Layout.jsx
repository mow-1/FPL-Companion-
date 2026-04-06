import { useState } from 'react'
import { NavLink, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { LayoutDashboard, Users, Zap, CalendarDays, Star, User, LogOut, Sun, Moon, Sparkles, Menu, X } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/players', label: 'Players', icon: Users },
  { to: '/predictions', label: 'Predictions', icon: Zap },
  { to: '/fixtures', label: 'Fixtures', icon: CalendarDays },
  { to: '/my-team', label: 'My Team', icon: Star },
  { to: '/advice', label: 'AI Advice', icon: Sparkles },
  { to: '/profile', label: 'Profile', icon: User },
]

function SidebarContent({ user, dark, toggle, handleLogout, onClose }) {
  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-6 border-b border-slate-200/50 dark:border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/25 flex-shrink-0">
            <Zap className="w-4 h-4 text-white" fill="white" />
          </div>
          <h1 className="text-lg tracking-tight text-slate-900 dark:text-white">
            <span className="font-bold">FPL</span>
            <span className="font-light text-slate-500 dark:text-slate-400"> Assistant</span>
          </h1>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={toggle}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
            title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors md:hidden"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                'relative flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors',
                isActive
                  ? 'bg-cyan-500/10 text-cyan-500 dark:text-cyan-400'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white'
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span>{label}</span>
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="p-4 border-t border-slate-200/50 dark:border-white/5">
        {user && (
          <Link
            to="/profile"
            onClick={onClose}
            className="flex items-center gap-3 mb-3 px-3 py-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0 shadow-md shadow-cyan-500/25">
              {user.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-900 dark:text-white truncate leading-tight">{user.username}</p>
              {user.fpl_team_id
                ? <p className="text-xs text-cyan-500 dark:text-cyan-400 leading-tight">Team #{user.fpl_team_id}</p>
                : <p className="text-xs text-yellow-500 leading-tight">Set FPL Team ID</p>
              }
            </div>
          </Link>
        )}
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-slate-500 dark:text-slate-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  )
}

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const { dark, toggle } = useTheme()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-slate-100 dark:bg-[#0B0F19] text-slate-800 dark:text-slate-200 overflow-hidden">

      {/* Ambient background */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-900/10 dark:bg-cyan-900/20 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/10 dark:bg-blue-900/20 blur-[120px]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px]" />
      </div>

      {/* Desktop sidebar */}
      <aside className="w-72 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-sm border-r border-slate-200/50 dark:border-white/5 flex-col hidden md:flex flex-shrink-0 relative z-10">
        <SidebarContent user={user} dark={dark} toggle={toggle} handleLogout={handleLogout} onClose={null} />
      </aside>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              key="sidebar"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 left-0 w-72 bg-white dark:bg-[#0f172a] border-r border-slate-200/50 dark:border-white/5 flex flex-col z-50 md:hidden"
            >
              <SidebarContent user={user} dark={dark} toggle={toggle} handleLogout={handleLogout} onClose={() => setMobileOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden min-w-0 relative z-10">

        {/* Mobile top bar */}
        <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-sm border-b border-slate-200/50 dark:border-white/5 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-cyan-500/25">
              <Zap className="w-3.5 h-3.5 text-white" fill="white" />
            </div>
            <h1 className="text-base tracking-tight text-slate-900 dark:text-white">
              <span className="font-bold">FPL</span>
              <span className="font-light text-slate-500 dark:text-slate-400"> Assistant</span>
            </h1>
          </div>
          <button
            onClick={toggle}
            className="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </header>

        {/* Scrollable area */}
        <div className="flex-1 overflow-y-auto relative">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] pointer-events-none z-0"
            style={{ background: 'radial-gradient(ellipse at center top, rgba(6,182,212,0.07) 0%, transparent 70%)' }}
          />
          <div className="relative z-10 p-4 md:p-8 pb-24 md:pb-8">
            {children}
          </div>
        </div>
      </main>

      {/* Mobile bottom navigation bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-white/97 dark:bg-[#0f172a]/97 backdrop-blur-xl border-t border-slate-200 dark:border-white/8">
        <div className="flex items-stretch h-16">
          {[
            { to: '/dashboard',   label: 'Home',    icon: LayoutDashboard, end: true },
            { to: '/predictions', label: 'Picks',   icon: Zap },
            { to: '/my-team',     label: 'My Team', icon: Star },
            { to: '/advice',      label: 'AI',      icon: Sparkles },
          ].map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className="flex-1">
              {({ isActive }) => (
                <div className="h-full flex flex-col items-center justify-center gap-0.5">
                  <Icon className={`w-5 h-5 transition-colors ${isActive ? 'text-cyan-500 dark:text-cyan-400' : 'text-slate-400 dark:text-slate-500'}`} />
                  <span className={`text-[10px] font-medium transition-colors leading-none ${isActive ? 'text-cyan-500 dark:text-cyan-400' : 'text-slate-400 dark:text-slate-500'}`}>
                    {label}
                  </span>
                  {isActive && <div className="absolute bottom-0 w-8 h-0.5 bg-cyan-400 rounded-full" />}
                </div>
              )}
            </NavLink>
          ))}
          <button onClick={() => setMobileOpen(true)} className="flex-1 flex flex-col items-center justify-center gap-0.5">
            <Menu className="w-5 h-5 text-slate-400 dark:text-slate-500" />
            <span className="text-[10px] font-medium text-slate-400 dark:text-slate-500 leading-none">More</span>
          </button>
        </div>
      </nav>
    </div>
  )
}
