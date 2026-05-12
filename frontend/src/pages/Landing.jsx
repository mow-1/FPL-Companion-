import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { ArrowRight, Lock, Shield, TrendingUp, Zap, BarChart2, Users, Star, CheckCircle2 } from 'lucide-react'
import api from '../api/client'
import PlayerPhoto from '../components/PlayerPhoto'

/* ── FPL Football Logo ─────────────────────────────────────────── */
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

/* ── Aerial Pitch SVG (hero background) ──────────────────────────── */
function PitchBackground() {
  return (
    <svg
      viewBox="0 0 800 480"
      className="absolute inset-0 w-full h-full"
      preserveAspectRatio="xMidYMid slice"
      style={{ opacity: 0.07 }}
    >
      {/* Pitch base */}
      <rect width="800" height="480" fill="#004d1a" />
      {/* Alternating grass stripes */}
      {Array.from({ length: 8 }).map((_, i) => (
        <rect key={i} x={i * 100} y="0" width="50" height="480" fill="rgba(0,80,30,0.4)" />
      ))}
      {/* Outer boundary */}
      <rect x="30" y="30" width="740" height="420" stroke="white" strokeWidth="2" fill="none" />
      {/* Centre line */}
      <line x1="400" y1="30" x2="400" y2="450" stroke="white" strokeWidth="1.5" />
      {/* Centre circle */}
      <circle cx="400" cy="240" r="80" stroke="white" strokeWidth="1.5" fill="none" />
      <circle cx="400" cy="240" r="3" fill="white" />
      {/* Left penalty area */}
      <rect x="30" y="140" width="130" height="200" stroke="white" strokeWidth="1.5" fill="none" />
      {/* Left 6-yard box */}
      <rect x="30" y="185" width="50" height="110" stroke="white" strokeWidth="1.5" fill="none" />
      {/* Left penalty spot */}
      <circle cx="105" cy="240" r="3" fill="white" />
      {/* Left penalty arc */}
      <path d="M 160 185 A 80 80 0 0 0 160 295" stroke="white" strokeWidth="1.5" fill="none" />
      {/* Right penalty area */}
      <rect x="640" y="140" width="130" height="200" stroke="white" strokeWidth="1.5" fill="none" />
      {/* Right 6-yard box */}
      <rect x="720" y="185" width="50" height="110" stroke="white" strokeWidth="1.5" fill="none" />
      {/* Right penalty spot */}
      <circle cx="695" cy="240" r="3" fill="white" />
      {/* Right penalty arc */}
      <path d="M 640 185 A 80 80 0 0 1 640 295" stroke="white" strokeWidth="1.5" fill="none" />
      {/* Corner arcs */}
      <path d="M 30 45 A 15 15 0 0 1 45 30" stroke="white" strokeWidth="1" fill="none" />
      <path d="M 770 30 A 15 15 0 0 1 785 45" stroke="white" strokeWidth="1" fill="none" />
      <path d="M 785 435 A 15 15 0 0 1 770 450" stroke="white" strokeWidth="1" fill="none" />
      <path d="M 45 450 A 15 15 0 0 1 30 435" stroke="white" strokeWidth="1" fill="none" />
    </svg>
  )
}

/* ── Position style map ─────────────────────────────────────────── */
const POS_STYLE = {
  GK:         { label: 'GK',  bg: '#f0a500', text: '#0d001a' },
  DEF:        { label: 'DEF', bg: '#3b82f6', text: '#fff'    },
  MID:        { label: 'MID', bg: '#8b5cf6', text: '#fff'    },
  FWD:        { label: 'FWD', bg: '#e90052', text: '#fff'    },
  Goalkeeper: { label: 'GK',  bg: '#f0a500', text: '#0d001a' },
  Defender:   { label: 'DEF', bg: '#3b82f6', text: '#fff'    },
  Midfielder: { label: 'MID', bg: '#8b5cf6', text: '#fff'    },
  Forward:    { label: 'FWD', bg: '#e90052', text: '#fff'    },
}
const posStyle = (pos) => POS_STYLE[pos] ?? { label: pos?.slice(0,3)?.toUpperCase() ?? '?', bg: '#374151', text: '#fff' }

/* ── Player row ─────────────────────────────────────────────────── */
function PlayerRow({ player, rank, blurred }) {
  const ps = posStyle(player.player_position)
  return (
    <div className={`relative flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors
      ${blurred ? 'select-none overflow-hidden' : 'hover:bg-white/5'}`}
      style={{ border: '1px solid rgba(0,255,135,0.08)', background: 'rgba(255,255,255,0.03)' }}>
      {blurred ? (
        <>
          <span className="w-5 text-center text-sm font-mono blur-sm" style={{ color: 'rgba(255,255,255,0.3)' }}>{rank}</span>
          <div className="w-9 h-9 rounded-full blur-sm" style={{ background: 'rgba(255,255,255,0.1)' }} />
          <div className="flex-1 space-y-1.5 blur-sm">
            <div className="h-3 rounded w-28" style={{ background: 'rgba(255,255,255,0.15)' }} />
            <div className="h-2.5 rounded w-20" style={{ background: 'rgba(255,255,255,0.08)' }} />
          </div>
          <div className="text-right blur-sm">
            <div className="h-4 rounded w-10 ml-auto" style={{ background: 'rgba(0,255,135,0.2)' }} />
          </div>
        </>
      ) : (
        <>
          <span className="w-5 text-center text-sm font-mono font-bold shrink-0" style={{ color: 'rgba(255,255,255,0.35)' }}>{rank}</span>
          <PlayerPhoto code={player.player_photo_code} name={player.player_name} pos={ps.label} size="md" />
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-semibold truncate">{player.player_name}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-xs font-bold px-1.5 py-0.5 rounded text-[10px] leading-none"
                style={{ background: ps.bg, color: ps.text }}>{ps.label}</span>
              <span className="text-xs truncate" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {player.player_team} · £{player.player_price?.toFixed(1)}m
              </span>
            </div>
          </div>
          <div className="text-right shrink-0">
            <p className="font-score font-bold text-lg leading-none" style={{ color: '#00ff87' }}>
              {Number(player.predicted_points).toFixed(1)}
            </p>
            <p className="text-[10px] leading-none mt-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>pts</p>
          </div>
        </>
      )}
    </div>
  )
}

/* ── Feature cards ─────────────────────────────────────────────── */
const features = [
  {
    icon: Star,
    title: 'Captain Picks',
    desc: 'A clear captain every gameweek — ranked by form, fixture, and historical output.',
    accent: '#00ff87',
  },
  {
    icon: TrendingUp,
    title: 'Smart Transfers',
    desc: 'Know exactly who to bring in. Ranked by differential value, ownership, and fixtures.',
    accent: '#e90052',
  },
  {
    icon: Zap,
    title: 'Best Team Builder',
    desc: 'AI builds the strongest possible squad for the next GW — no budget limit, FPL rules applied.',
    accent: '#f0a500',
  },
  {
    icon: Shield,
    title: 'Fixture Planner',
    desc: 'Colour-coded difficulty calendar. Plan transfers 5 weeks ahead — never get caught by a blank.',
    accent: '#8b5cf6',
  },
  {
    icon: BarChart2,
    title: 'GW Track Record',
    desc: 'See how every prediction performed since GW1. Transparent accuracy, not marketing numbers.',
    accent: '#3b82f6',
  },
  {
    icon: Users,
    title: 'Live Squad Sync',
    desc: 'Link your FPL ID in seconds. Every recommendation is tailored to what you actually own.',
    accent: '#00d4ff',
  },
]

const stats = [
  { value: '9/10',   label: 'Predictions within 2 pts', sub: 'accuracy' },
  { value: '38',     label: 'GWs of advice per season',  sub: 'coverage' },
  { value: '10 yrs', label: 'Of Premier League data',    sub: 'trained on' },
]

export default function Landing() {
  const [topPlayers, setTopPlayers] = useState([])
  const [gwName, setGwName] = useState('')
  const [loadingPlayers, setLoadingPlayers] = useState(true)

  useEffect(() => {
    api.get('/predictions/?limit=10')
      .then(r => {
        const data = r.data?.results ?? r.data ?? []
        setTopPlayers(data.slice(0, 10))
        if (data[0]?.gameweek_name) setGwName(data[0].gameweek_name)
      })
      .catch(() => {})
      .finally(() => setLoadingPlayers(false))
  }, [])

  return (
    <div className="min-h-screen overflow-hidden selection:bg-green-400/20"
      style={{ background: '#0d001a', color: '#f0f0f0', fontFamily: 'Inter, sans-serif' }}>

      {/* Ambient glows */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-5%] w-[55%] h-[55%] rounded-full blur-[180px]"
          style={{ background: 'radial-gradient(ellipse, rgba(55,0,60,0.5) 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-15%] right-[-5%] w-[45%] h-[45%] rounded-full blur-[140px]"
          style={{ background: 'radial-gradient(ellipse, rgba(0,255,135,0.07) 0%, transparent 70%)' }} />
        <div className="absolute top-[40%] left-[50%] w-[30%] h-[30%] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(ellipse, rgba(233,0,82,0.05) 0%, transparent 70%)' }} />
      </div>

      {/* ── Navbar ──────────────────────────────────────────────────── */}
      <nav className="relative z-10 sticky top-0 backdrop-blur-md"
        style={{ borderBottom: '1px solid rgba(0,255,135,0.08)', background: 'rgba(13,0,26,0.85)' }}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FootballLogo size={32} />
            <span className="font-display font-bold text-lg text-white tracking-wide">
              FPL <span style={{ color: '#00ff87' }}>Scout</span>
            </span>
          </div>
          <div className="flex items-center gap-5">
            {gwName && (
              <span className="hidden sm:flex gw-chip items-center gap-1">
                {gwName}
              </span>
            )}
            <Link to="/login"
              className="text-sm font-medium hidden sm:block transition-colors"
              style={{ color: 'rgba(255,255,255,0.55)' }}
              onMouseEnter={e => e.target.style.color = '#fff'}
              onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.55)'}>
              Sign In
            </Link>
            <Link to="/register"
              className="px-5 py-2 rounded-md text-sm font-bold transition-all glow-green"
              style={{ background: '#00ff87', color: '#0d001a' }}>
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">

        {/* ── Hero ──────────────────────────────────────────────────── */}
        <section className="relative pt-20 pb-24 px-6 overflow-hidden">
          {/* Pitch as background */}
          <div className="absolute inset-0">
            <PitchBackground />
          </div>
          {/* Stadium light effect */}
          <div className="absolute inset-0 pointer-events-none"
            style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 0%, rgba(55,0,60,0.0) 0%, rgba(13,0,26,0.8) 100%)' }} />

          <div className="relative max-w-5xl mx-auto text-center">

            {/* GW chip */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="inline-flex items-center gap-2 mb-8"
            >
              <span className="gw-chip">{gwName || 'GW38 · 2025/26'}</span>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full"
                style={{ background: 'rgba(233,0,82,0.15)', color: '#e90052', border: '1px solid rgba(233,0,82,0.25)' }}>
                ● LIVE PREDICTIONS
              </span>
            </motion.div>

            {/* Title */}
            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="font-display font-bold leading-none mb-6"
              style={{ fontSize: 'clamp(52px, 9vw, 96px)', letterSpacing: '-0.02em' }}
            >
              <span className="text-white">Win Your </span>
              <span style={{ color: '#00ff87' }}>Mini-League.</span>
            </motion.h1>

            {/* Sub */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-lg md:text-xl mb-10 max-w-2xl mx-auto leading-relaxed"
              style={{ color: 'rgba(255,255,255,0.55)' }}
            >
              Every gameweek, get a ranked captain pick, data-driven transfer targets, and
              an AI-built best XI — trained on a decade of Premier League results.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12"
            >
              <Link to="/register"
                className="w-full sm:w-auto px-8 py-4 rounded-lg font-bold text-base transition-all flex items-center justify-center gap-2 group glow-green"
                style={{ background: '#00ff87', color: '#0d001a' }}>
                Start Free — No Credit Card
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link to="/login"
                className="w-full sm:w-auto px-8 py-4 rounded-lg font-semibold text-base transition-all flex items-center justify-center gap-2"
                style={{ border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.75)' }}>
                Sign In
              </Link>
            </motion.div>

            {/* Trust perks */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="flex flex-wrap items-center justify-center gap-x-7 gap-y-3 text-sm"
              style={{ color: 'rgba(255,255,255,0.35)' }}
            >
              {['No ads or upsells', 'Sync with your real FPL team', 'Updated every gameweek', 'Works on mobile'].map((p, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" style={{ color: '#00ff87' }} />
                  <span>{p}</span>
                </div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ── Stats strip ─────────────────────────────────────────── */}
        <section className="py-14 px-6" style={{ borderTop: '1px solid rgba(0,255,135,0.08)', borderBottom: '1px solid rgba(0,255,135,0.08)', background: 'rgba(0,255,135,0.02)' }}>
          <div className="max-w-5xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-0 divide-y md:divide-y-0 md:divide-x" style={{ '--tw-divide-opacity': 0.12, borderColor: 'rgba(0,255,135,0.12)' }}>
              {stats.map((s, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  className="flex flex-col items-center text-center py-8 md:py-0 first:pt-0 last:pb-0"
                >
                  <div className="font-score font-bold leading-none mb-2 glow-green-text"
                    style={{ fontSize: 'clamp(44px, 7vw, 60px)', color: '#00ff87' }}>
                    {s.value}
                  </div>
                  <div className="text-white font-semibold text-sm mb-0.5">{s.label}</div>
                  <div className="text-xs uppercase tracking-widest" style={{ color: 'rgba(0,255,135,0.4)' }}>{s.sub}</div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Top Predicted Players ───────────────────────────────── */}
        <section className="py-24 px-6">
          <div className="max-w-2xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="text-center mb-8"
            >
              {/* Section label */}
              <div className="inline-block gw-chip mb-4">
                {gwName ? `${gwName} Top Picks` : 'This Gameweek Top Picks'}
              </div>
              <h2 className="font-display font-bold text-white mb-2" style={{ fontSize: 'clamp(28px, 5vw, 40px)' }}>
                Who to Pick Right Now
              </h2>
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
                AI-ranked by expected points. Sign in to see the full list and build your squad.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="rounded-2xl overflow-hidden"
              style={{ border: '1px solid rgba(0,255,135,0.15)', background: 'rgba(0,255,135,0.02)' }}
            >
              {/* Terminal-style header */}
              <div className="h-10 flex items-center px-4 gap-2"
                style={{ borderBottom: '1px solid rgba(0,255,135,0.1)', background: 'rgba(0,255,135,0.04)' }}>
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#e90052' }} />
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#f0a500' }} />
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#00ff87' }} />
                <span className="ml-2 text-xs font-mono" style={{ color: 'rgba(0,255,135,0.45)' }}>
                  fpl-scout · predictions · {gwName || 'GW38'}
                </span>
              </div>

              <div className="p-4 space-y-2">
                {loadingPlayers ? (
                  Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-lg animate-pulse"
                      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,255,135,0.06)' }}>
                      <div className="w-5 h-3 rounded" style={{ background: 'rgba(255,255,255,0.1)' }} />
                      <div className="w-9 h-9 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }} />
                      <div className="flex-1 space-y-2">
                        <div className="w-32 h-3 rounded" style={{ background: 'rgba(255,255,255,0.12)' }} />
                        <div className="w-20 h-2.5 rounded" style={{ background: 'rgba(255,255,255,0.07)' }} />
                      </div>
                      <div className="w-10 h-4 rounded" style={{ background: 'rgba(0,255,135,0.15)' }} />
                    </div>
                  ))
                ) : topPlayers.length === 0 ? (
                  <p className="text-center py-8 text-sm" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    No predictions yet — check back after the next sync.
                  </p>
                ) : (
                  <>
                    {topPlayers.slice(0, 5).map((p, i) => (
                      <PlayerRow key={p.id} player={p} rank={i + 1} blurred={false} />
                    ))}
                    {topPlayers.length > 5 && (
                      <div className="relative">
                        <div className="space-y-2 pointer-events-none">
                          {topPlayers.slice(5, 10).map((p, i) => (
                            <PlayerRow key={p.id} player={p} rank={i + 6} blurred />
                          ))}
                        </div>
                        <div className="absolute inset-0 flex items-center justify-center z-20">
                          <div className="flex flex-col items-center gap-4 px-7 py-6 rounded-2xl text-center shadow-2xl"
                            style={{ background: 'rgba(13,0,26,0.92)', border: '1px solid rgba(0,255,135,0.2)', backdropFilter: 'blur(12px)' }}>
                            <Lock className="w-6 h-6" style={{ color: '#00ff87' }} />
                            <div>
                              <p className="font-display font-bold text-white text-base mb-1">See all 10 picks</p>
                              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Sign in to unlock the full ranked list</p>
                            </div>
                            <Link to="/login"
                              className="px-6 py-2.5 rounded-lg text-sm font-bold transition-all glow-green"
                              style={{ background: '#00ff87', color: '#0d001a' }}>
                              Sign In to See More
                            </Link>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </motion.div>
          </div>
        </section>

        {/* ── Features ──────────────────────────────────────────────── */}
        <section className="py-24 px-6" style={{ borderTop: '1px solid rgba(0,255,135,0.06)' }}>
          <div className="max-w-6xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="text-center mb-16"
            >
              <div className="inline-block gw-chip mb-5">WHAT YOU GET</div>
              <h2 className="font-display font-bold text-white mb-4"
                style={{ fontSize: 'clamp(28px, 5vw, 44px)' }}>
                Every Tool You Need to Get the Edge
              </h2>
              <p className="text-base max-w-xl mx-auto" style={{ color: 'rgba(255,255,255,0.4)' }}>
                Built by FPL obsessives. Powered by AI that's been analysing Premier League data since 2015.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {features.map((f, i) => (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.06 }}
                  className="relative rounded-xl p-6 group transition-all hover:-translate-y-1 hover:shadow-xl"
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.07)',
                  }}
                >
                  {/* Accent line */}
                  <div className="absolute top-0 left-6 right-6 h-px rounded-full"
                    style={{ background: `linear-gradient(90deg, transparent, ${f.accent}40, transparent)` }} />

                  <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                    style={{ background: `${f.accent}15`, border: `1px solid ${f.accent}25` }}>
                    <f.icon className="w-6 h-6" style={{ color: f.accent }} />
                  </div>
                  <h3 className="font-display font-bold text-white text-lg mb-2">{f.title}</h3>
                  <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>{f.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Final CTA ─────────────────────────────────────────────── */}
        <section className="py-24 px-6">
          <div className="max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="relative rounded-2xl p-12 text-center overflow-hidden"
              style={{ border: '1px solid rgba(0,255,135,0.2)', background: 'rgba(0,255,135,0.03)' }}
            >
              {/* Corner pitch lines */}
              <div className="absolute top-4 left-4 w-12 h-12 border-l-2 border-t-2 rounded-tl-lg opacity-20"
                style={{ borderColor: '#00ff87' }} />
              <div className="absolute bottom-4 right-4 w-12 h-12 border-r-2 border-b-2 rounded-br-lg opacity-20"
                style={{ borderColor: '#00ff87' }} />
              <div className="absolute inset-0 pointer-events-none"
                style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 100%, rgba(0,255,135,0.05) 0%, transparent 70%)' }} />

              <div className="relative z-10">
                <div className="inline-block gw-chip mb-6">READY TO PLAY?</div>
                <h2 className="font-display font-bold text-white mb-4"
                  style={{ fontSize: 'clamp(28px, 5vw, 42px)' }}>
                  Outsmart Your Mini-League<br />Starting This Gameweek
                </h2>
                <p className="mb-8 max-w-md mx-auto" style={{ color: 'rgba(255,255,255,0.4)' }}>
                  Create a free account, link your FPL Team ID, and get your first AI-backed recommendation in under 2 minutes.
                </p>
                <Link to="/register"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-lg font-bold text-base transition-all group glow-green"
                  style={{ background: '#00ff87', color: '#0d001a' }}>
                  Create Free Account
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="relative z-10 py-8 text-center text-sm"
        style={{ borderTop: '1px solid rgba(0,255,135,0.08)', color: 'rgba(255,255,255,0.2)' }}>
        <span className="font-display font-bold" style={{ color: '#00ff87' }}>FPL Scout</span>
        &nbsp;·&nbsp;2025/26 Season&nbsp;·&nbsp;Trained on 10 years of Premier League data
      </footer>
    </div>
  )
}
