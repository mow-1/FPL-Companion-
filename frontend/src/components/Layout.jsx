import { useState } from 'react'
import { NavLink, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { LayoutDashboard, Users, Zap, CalendarDays, Star, User, LogOut, Sun, Moon, Sparkles, Menu, X, Activity } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { cn } from '@/lib/utils'

/* ── FPL Football Logo ─────────────────────────────────────────── */
function FootballLogo({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <circle cx="20" cy="20" r="18" fill="#00ff87" opacity="0.12" />
      <circle cx="20" cy="20" r="16" stroke="#00ff87" strokeWidth="1.5" fill="none" />
      {/* Top pentagon */}
      <polygon points="20,5 23.5,10 20,13.5 16.5,10" fill="#00ff87" />
      {/* Right top */}
      <polygon points="32,13 30,18.5 25.5,18 24,12.5" fill="#00ff87" opacity="0.75" />
      {/* Right bottom */}
      <polygon points="30,27 25.5,28 23.5,23 27,19.5" fill="#00ff87" opacity="0.75" />
      {/* Bottom */}
      <polygon points="20,33 16.5,28 20,25.5 23.5,28" fill="#00ff87" opacity="0.75" />
      {/* Left bottom */}
      <polygon points="10,27 13,19.5 16.5,23 14.5,28" fill="#00ff87" opacity="0.5" />
      {/* Left top */}
      <polygon points="8,13 16,12.5 14.5,18 10,18.5" fill="#00ff87" opacity="0.5" />
      {/* Center hexagon outline */}
      <polygon points="20,13.5 25.5,18 24,23 16.5,23 14.5,18 16.5,13.5"
        stroke="#00ff87" strokeWidth="0.8" fill="none" opacity="0.4" />
    </svg>
  )
}

const navItems = [
  { to: '/dashboard',   label: 'Dashboard',   icon: LayoutDashboard, end: true, badge: 'LIVE' },
  { to: '/players',     label: 'Players',      icon: Users },
  { to: '/predictions', label: 'Predictions',  icon: Activity },
  { to: '/fixtures',    label: 'Fixtures',     icon: CalendarDays },
  { to: '/my-team',     label: 'My Team',      icon: Star },
  { to: '/advice',      label: 'AI Advice',    icon: Sparkles },
  { to: '/profile',     label: 'Profile',      icon: User },
]

function SidebarContent({ user, dark, toggle, handleLogout, onClose }) {
  return (
    <div className="flex flex-col h-full" style={{ background: '#130022' }}>

      {/* Logo */}
      <div className="px-5 py-5 flex items-center justify-between"
        style={{ borderBottom: '1px solid rgba(0,255,135,0.1)' }}>
        <div className="flex items-center gap-3">
          <FootballLogo size={36} />
          <div>
            <h1 className="font-display text-white leading-none tracking-wide" style={{ fontSize: '18px', fontWeight: 700 }}>
              FPL <span style={{ color: '#00ff87' }}>Scout</span>
            </h1>
            <p className="text-[10px] leading-none mt-0.5" style={{ color: 'rgba(0,255,135,0.5)', fontFamily: 'Rajdhani, sans-serif', letterSpacing: '0.1em' }}>
              2025/26 SEASON
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={toggle}
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: 'rgba(255,255,255,0.4)' }}
            title={dark ? 'Light mode' : 'Dark mode'}
          >
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          {onClose && (
            <button onClick={onClose} className="p-1.5 rounded-lg md:hidden"
              style={{ color: 'rgba(255,255,255,0.4)' }}>
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, end, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                'relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group',
                isActive
                  ? 'text-[#0d001a]'
                  : 'hover:bg-white/5'
              )
            }
            style={({ isActive }) => isActive ? {
              background: 'linear-gradient(90deg, #00ff87 0%, #00d46f 100%)',
              color: '#0d001a',
            } : { color: 'rgba(255,255,255,0.55)' }}
          >
            {({ isActive }) => (
              <>
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span style={{ fontWeight: isActive ? 700 : 500 }}>{label}</span>
                {badge && (
                  <span className="ml-auto text-[9px] font-bold tracking-wider px-1.5 py-0.5 rounded"
                    style={{
                      background: isActive ? 'rgba(0,0,0,0.2)' : 'rgba(0,255,135,0.15)',
                      color: isActive ? '#0d001a' : '#00ff87',
                    }}>
                    {badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="px-3 py-4" style={{ borderTop: '1px solid rgba(0,255,135,0.1)' }}>
        {user && (
          <Link
            to="/profile"
            onClick={onClose}
            className="flex items-center gap-3 mb-2 px-3 py-2.5 rounded-lg transition-colors hover:bg-white/5"
          >
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #00ff87 0%, #00a855 100%)', color: '#0d001a' }}>
              {user.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate leading-tight">{user.username}</p>
              {user.fpl_team_id
                ? <p className="text-xs leading-tight" style={{ color: '#00ff87' }}>Team #{user.fpl_team_id}</p>
                : <p className="text-xs leading-tight text-yellow-400">Link your FPL team</p>
              }
            </div>
          </Link>
        )}
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors hover:bg-red-500/10"
          style={{ color: 'rgba(255,255,255,0.35)' }}
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
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
    <div className="flex h-screen overflow-hidden" style={{ background: '#0d001a', color: '#f0f0f0' }}>

      {/* Ambient background */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-[20%] w-[40%] h-[50%] rounded-full blur-[150px]"
          style={{ background: 'radial-gradient(ellipse, rgba(55,0,60,0.35) 0%, transparent 70%)' }} />
        <div className="absolute bottom-0 right-[10%] w-[35%] h-[40%] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(ellipse, rgba(0,255,135,0.06) 0%, transparent 70%)' }} />
      </div>

      {/* Desktop sidebar */}
      <aside className="w-64 hidden md:flex flex-col flex-shrink-0 relative z-10"
        style={{ borderRight: '1px solid rgba(0,255,135,0.08)' }}>
        <SidebarContent user={user} dark={dark} toggle={toggle} handleLogout={handleLogout} onClose={null} />
      </aside>

      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 md:hidden"
              style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              key="sidebar"
              initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 left-0 w-64 flex flex-col z-50 md:hidden"
              style={{ borderRight: '1px solid rgba(0,255,135,0.1)' }}
            >
              <SidebarContent user={user} dark={dark} toggle={toggle} handleLogout={handleLogout} onClose={() => setMobileOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden min-w-0 relative z-10">

        {/* Mobile topbar */}
        <header className="md:hidden flex items-center justify-between px-4 py-3 flex-shrink-0"
          style={{ background: '#130022', borderBottom: '1px solid rgba(0,255,135,0.1)' }}>
          <div className="flex items-center gap-2">
            <FootballLogo size={28} />
            <span className="font-display font-bold text-white text-base tracking-wide">
              FPL <span style={{ color: '#00ff87' }}>Scout</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={toggle} className="p-2 rounded-lg" style={{ color: 'rgba(255,255,255,0.4)' }}>
              {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <button onClick={() => setMobileOpen(true)} className="p-2 rounded-lg" style={{ color: 'rgba(255,255,255,0.4)' }}>
              <Menu className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto relative">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[350px] pointer-events-none z-0"
            style={{ background: 'radial-gradient(ellipse at center top, rgba(0,255,135,0.04) 0%, transparent 70%)' }} />
          <div className="relative z-10 p-4 md:p-7 pb-24 md:pb-7">
            {children}
          </div>
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30"
        style={{ background: '#130022', borderTop: '1px solid rgba(0,255,135,0.1)' }}>
        <div className="flex items-stretch h-16">
          {[
            { to: '/dashboard',   label: 'Home',   icon: LayoutDashboard, end: true },
            { to: '/predictions', label: 'Picks',  icon: Activity },
            { to: '/my-team',     label: 'My Team',icon: Star },
            { to: '/advice',      label: 'AI',     icon: Sparkles },
          ].map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className="flex-1">
              {({ isActive }) => (
                <div className="h-full flex flex-col items-center justify-center gap-0.5">
                  <Icon className="w-5 h-5 transition-colors"
                    style={{ color: isActive ? '#00ff87' : 'rgba(255,255,255,0.35)' }} />
                  <span className="text-[10px] font-medium leading-none transition-colors"
                    style={{ color: isActive ? '#00ff87' : 'rgba(255,255,255,0.35)' }}>
                    {label}
                  </span>
                  {isActive && (
                    <div className="absolute bottom-0 w-8 h-0.5 rounded-full" style={{ background: '#00ff87' }} />
                  )}
                </div>
              )}
            </NavLink>
          ))}
          <button onClick={() => setMobileOpen(true)} className="flex-1 flex flex-col items-center justify-center gap-0.5">
            <Menu className="w-5 h-5" style={{ color: 'rgba(255,255,255,0.35)' }} />
            <span className="text-[10px] font-medium leading-none" style={{ color: 'rgba(255,255,255,0.35)' }}>More</span>
          </button>
        </div>
      </nav>
    </div>
  )
}
