import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import {
  Brain, TrendingUp, Zap, Shield, BarChart2, Users,
  ArrowRight, CheckCircle2, Sun, Moon, Lock,
} from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import api from '../api/client'
import PlayerPhoto from '../components/PlayerPhoto'

const POS_STYLE = {
  GK:         { label: 'GK',  bg: 'bg-yellow-500/15', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  DEF:        { label: 'DEF', bg: 'bg-blue-500/15',   text: 'text-blue-400',   border: 'border-blue-500/30'   },
  MID:        { label: 'MID', bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30' },
  FWD:        { label: 'FWD', bg: 'bg-orange-500/15', text: 'text-orange-400', border: 'border-orange-500/30' },
  // long-form fallbacks
  Goalkeeper: { label: 'GK',  bg: 'bg-yellow-500/15', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  Defender:   { label: 'DEF', bg: 'bg-blue-500/15',   text: 'text-blue-400',   border: 'border-blue-500/30'   },
  Midfielder: { label: 'MID', bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30' },
  Forward:    { label: 'FWD', bg: 'bg-orange-500/15', text: 'text-orange-400', border: 'border-orange-500/30' },
}
const posStyle = (pos) => POS_STYLE[pos] ?? { label: pos?.slice(0,3).toUpperCase() ?? '?', bg: 'bg-slate-500/15', text: 'text-slate-500 dark:text-slate-400', border: 'border-slate-500/30' }

function PlayerRow({ player, rank, blurred }) {
  const ps = posStyle(player.player_position)
  return (
    <div className={`relative flex items-center gap-3 px-4 py-2.5 rounded-lg border border-slate-200/50 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] ${blurred ? 'select-none overflow-hidden' : ''}`}>
      {blurred ? (
        <>
          {/* blurred ghost content */}
          <span className="w-5 text-center text-slate-600 dark:text-slate-500 text-sm font-mono shrink-0 blur-sm">{rank}</span>
          <div className="w-9 h-9 rounded-full bg-slate-200 dark:bg-white/10 blur-sm" />
          <div className="flex-1 min-w-0 space-y-1.5 blur-sm">
            <div className="h-3 bg-slate-300 dark:bg-white/20 rounded w-28" />
            <div className="h-2.5 bg-slate-200 dark:bg-white/10 rounded w-20" />
          </div>
          <div className="text-right shrink-0 blur-sm">
            <div className="h-3.5 bg-slate-300 dark:bg-white/20 rounded w-8 ml-auto" />
          </div>
        </>
      ) : (
        <>
          <span className="w-5 text-center text-slate-600 dark:text-slate-500 text-sm font-mono shrink-0">{rank}</span>
          <PlayerPhoto
            code={player.player_photo_code}
            name={player.player_name}
            pos={ps.label}
            size="md"
          />
          <div className="flex-1 min-w-0">
            <p className="text-slate-900 dark:text-white text-sm font-semibold truncate">{player.player_name}</p>
            <p className="text-slate-600 dark:text-slate-500 text-xs truncate">{player.player_team} · £{player.player_price?.toFixed(1)}m</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-cyan-400 font-bold text-sm">{Number(player.predicted_points).toFixed(1)}</p>
            <p className="text-slate-700 dark:text-slate-600 text-xs">pts</p>
          </div>
        </>
      )}
    </div>
  )
}

const features = [
  { icon: Brain,     title: 'Captain Picks',         desc: 'Get a clear captain recommendation every gameweek based on form, upcoming fixtures, and historical scoring patterns.',  color: 'text-cyan-400',    bg: 'bg-cyan-500/10',    border: 'border-cyan-500/20'   },
  { icon: TrendingUp,title: 'Smart Transfers',       desc: 'Know exactly who to bring in and who to drop — ranked by form, fixtures, and how many managers already own them.',      color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20'},
  { icon: Zap,       title: 'Squad Builder',         desc: 'Set your budget and let the AI build the strongest possible squad for the next gameweek — automatically.',              color: 'text-yellow-400',  bg: 'bg-yellow-500/10',  border: 'border-yellow-500/20' },
  { icon: Shield,    title: 'Fixture Planner',       desc: 'See which teams have easy runs coming up. Plan your transfers weeks in advance with a colour-coded difficulty calendar.', color: 'text-purple-400',  bg: 'bg-purple-500/10',  border: 'border-purple-500/20' },
  { icon: BarChart2, title: 'Weekly Results',        desc: "See how our picks performed each gameweek so you always know how reliable the advice has been.",                         color: 'text-blue-400',    bg: 'bg-blue-500/10',    border: 'border-blue-500/20'   },
  { icon: Users,     title: 'Live Squad Sync',       desc: 'Link your FPL account in seconds. We sync your squad automatically so every recommendation is tailored to your team.',  color: 'text-rose-400',    bg: 'bg-rose-500/10',    border: 'border-rose-500/20'   },
]

const stats = [
  { value: '9/10',  label: 'Predictions land within 2 points' },
  { value: '38',    label: 'Gameweeks of advice per season' },
  { value: '10 yrs', label: 'Of Premier League data analysed' },
]

const perks = [
  'No ads, no upsells',
  'Sync with your real FPL team',
  'Updated every gameweek',
  'Works on mobile',
]

export default function Landing() {
  const { dark, toggle } = useTheme()
  const [topPlayers, setTopPlayers] = useState([])
  const [gwName, setGwName]         = useState('')
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
    <div className="min-h-screen bg-slate-100 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-50 font-sans overflow-hidden selection:bg-cyan-500/30">

      {/* Background effects */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-900/20 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/20 blur-[120px]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px]" />
      </div>

      {/* Navbar */}
      <nav className="relative z-10 border-b border-slate-200/50 dark:border-white/5 bg-slate-100 dark:bg-[#0B0F19]/50 backdrop-blur-md sticky top-0">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="font-bold text-xl tracking-tight">
            FPL <span className="text-cyan-400">Assistant</span>
          </span>
          <div className="flex items-center gap-6">
            <button
              onClick={toggle}
              className="text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
              title={dark ? 'Light mode' : 'Dark mode'}
            >
              {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <Link to="/login" className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors hidden sm:block">
              Sign In
            </Link>
            <Link to="/register" className="px-4 py-2 rounded-md bg-cyan-500 text-slate-950 text-sm font-semibold hover:bg-cyan-400 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">

        {/* Hero */}
        <section className="pt-24 md:pt-32 pb-20 px-6">
          <div className="max-w-4xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium tracking-wide uppercase mb-8"
            >
              <Zap className="w-3.5 h-3.5" />
              AI-Powered FPL Manager
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-[1.1]"
            >
              Your smartest FPL <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
                season starts here
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-lg md:text-xl text-slate-500 dark:text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed"
            >
              Every gameweek, get a clear captain pick, smart transfer suggestions, and
              an optimised squad — all powered by AI trained on a decade of Premier League data.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12"
            >
              <Link
                to="/register"
                className="w-full sm:w-auto px-8 py-3.5 rounded-md bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-base transition-all flex items-center justify-center gap-2 group shadow-[0_0_30px_-10px_rgba(6,182,212,0.5)]"
              >
                Start for free
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                to="/login"
                className="w-full sm:w-auto px-8 py-3.5 rounded-md bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white font-semibold text-base transition-all flex items-center justify-center gap-2"
              >
                Sign in
              </Link>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-sm text-slate-500 dark:text-slate-400"
            >
              {perks.map((perk, i) => (
                <div key={i} className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-500" />
                  <span>{perk}</span>
                </div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* Stats */}
        <section className="py-16 px-6 border-y border-slate-200/50 dark:border-white/5 bg-slate-50 dark:bg-white/[0.02] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/5 to-transparent" />
          <div className="max-w-5xl mx-auto relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-12 md:gap-8 divide-y md:divide-y-0 md:divide-x divide-slate-200 dark:divide-white/10">
              {stats.map((stat, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  className="flex flex-col items-center text-center pt-8 md:pt-0 first:pt-0"
                >
                  <div className="text-4xl md:text-5xl font-bold text-cyan-400 mb-2 drop-shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                    {stat.value}
                  </div>
                  <div className="text-slate-500 dark:text-slate-400 text-sm md:text-base">{stat.label}</div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Top predicted players preview */}
        <section className="py-24 px-6">
          <div className="max-w-2xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="text-center mb-10"
            >
              <h2 className="text-3xl md:text-4xl font-bold mb-3">
                Top Predicted Players
              </h2>
              <p className="text-slate-500 dark:text-slate-400">
                AI-ranked by expected points
                {gwName ? ` · ${gwName}` : ''}.
                Sign in to see the full list.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-100/60 dark:bg-[#111827]/60 backdrop-blur-xl overflow-hidden"
            >
              {/* Header */}
              <div className="h-10 border-b border-slate-200 dark:border-white/10 flex items-center px-4 gap-3 bg-slate-100 dark:bg-white/5">
                <div className="w-2.5 h-2.5 rounded-full bg-slate-600" />
                <div className="w-2.5 h-2.5 rounded-full bg-slate-600" />
                <div className="w-2.5 h-2.5 rounded-full bg-slate-600" />
                <span className="ml-2 text-slate-600 dark:text-slate-500 text-xs">fpl-assistant · predictions</span>
              </div>

              <div className="p-4 space-y-2">
                {loadingPlayers ? (
                  Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-4 px-4 py-3 rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200/50 dark:border-white/5 animate-pulse">
                      <div className="w-5 h-3 bg-slate-200 dark:bg-white/10 rounded" />
                      <div className="w-9 h-9 rounded-full bg-slate-200 dark:bg-white/10" />
                      <div className="flex-1 space-y-2">
                        <div className="w-32 h-3 bg-slate-200 dark:bg-white/15 rounded" />
                        <div className="w-20 h-2.5 bg-slate-200 dark:bg-white/10 rounded" />
                      </div>
                      <div className="w-8 h-4 bg-slate-200 dark:bg-white/10 rounded" />
                    </div>
                  ))
                ) : topPlayers.length === 0 ? (
                  <p className="text-center text-slate-600 dark:text-slate-500 py-8 text-sm">No predictions available yet.</p>
                ) : (
                  <>
                    {/* Top 5 — visible */}
                    {topPlayers.slice(0, 5).map((p, i) => (
                      <PlayerRow key={p.id} player={p} rank={i + 1} blurred={false} />
                    ))}

                    {/* Bottom 5 — blurred with overlay */}
                    {topPlayers.length > 5 && (
                      <div className="relative">
                        <div className="space-y-2 pointer-events-none">
                          {topPlayers.slice(5, 10).map((p, i) => (
                            <PlayerRow key={p.id} player={p} rank={i + 6} blurred={true} />
                          ))}
                        </div>
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
                          <div className="flex flex-col items-center gap-4 px-6 py-5 rounded-xl bg-slate-100 dark:bg-[#0B0F19]/80 border border-slate-200 dark:border-white/10 backdrop-blur-sm text-center shadow-xl">
                            <Lock className="w-6 h-6 text-cyan-400" />
                            <div>
                              <p className="text-slate-900 dark:text-white font-semibold text-sm mb-1">See all predictions</p>
                              <p className="text-slate-500 dark:text-slate-400 text-xs">Sign in to unlock the full ranked list</p>
                            </div>
                            <Link
                              to="/login"
                              className="px-5 py-2 rounded-md bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-sm font-semibold transition-colors"
                            >
                              Sign in to see more
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

        {/* Features */}
        <section className="py-24 px-6">
          <div className="max-w-6xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="text-center mb-16"
            >
              <h2 className="text-3xl md:text-4xl font-bold mb-4">Everything you need to stay ahead</h2>
              <p className="text-slate-500 dark:text-slate-400 text-lg max-w-xl mx-auto">
                Built by FPL enthusiasts, powered by AI that's obsessed with points.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {features.map((f, i) => (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.07 }}
                  className={`bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/8 hover:border-slate-300 dark:hover:border-white/15 rounded-xl p-6 transition-colors`}
                >
                  <div className={`w-12 h-12 rounded-xl ${f.bg} border ${f.border} flex items-center justify-center mb-4`}>
                    <f.icon className={`w-6 h-6 ${f.color}`} />
                  </div>
                  <h3 className="text-slate-900 dark:text-white font-semibold text-lg mb-2">{f.title}</h3>
                  <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">{f.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-24 px-6">
          <div className="max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="relative rounded-2xl border border-cyan-500/20 bg-slate-50 dark:bg-white/[0.03] p-12 text-center overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-500/5 pointer-events-none" />
              <h2 className="text-3xl font-bold mb-4 relative z-10">Ready to outsmart your mini-league?</h2>
              <p className="text-slate-500 dark:text-slate-400 mb-8 max-w-md mx-auto relative z-10">
                Create a free account, connect your FPL team ID, and get your first AI recommendation in minutes.
              </p>
              <Link
                to="/register"
                className="relative z-10 inline-flex items-center gap-2 px-8 py-3.5 rounded-md bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold transition-all shadow-[0_0_30px_-10px_rgba(6,182,212,0.5)] group"
              >
                Create free account
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-200/50 dark:border-white/5 py-8 text-center text-slate-600 dark:text-slate-500 text-sm">
        <span className="text-cyan-400 font-semibold">FPL Assistant</span> · 2025-26 Season · Powered by AI predictions
      </footer>
    </div>
  )
}
