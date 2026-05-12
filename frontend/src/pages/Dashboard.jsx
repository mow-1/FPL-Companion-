import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getDashboard, generateTransfers, generateCaptain, syncSquad } from '../api/fpl'
import { useAuth } from '../context/AuthContext'
import { TrendingUp, Wallet, Trophy, Target, RefreshCw, Zap, ArrowRight, Crown, ArrowRightLeft, ArrowDownRight, ArrowUpRight } from 'lucide-react'
import { getTeamColor } from '../theme/teamColors'
import { motion } from 'motion/react'
import PlayerPhoto, { PlayerPhotoCard } from '../components/PlayerPhoto'
import PitchSVG from '../components/PitchSVG'

// ─── Shared design tokens ──────────────────────────────────────────────────────

const POS_BADGE = {
  GK:  'bg-[#F0A500]/20 text-yellow-300 border-[#F0A500]/40',
  DEF: 'bg-blue-400/20  text-blue-300   border-blue-400/40',
  MID: 'bg-cyan-400/20  text-cyan-300   border-cyan-400/40',
  FWD: 'bg-red-400/20   text-red-300    border-red-400/40',
}

const POS_BAR_COLOR = {
  GK:  'bg-yellow-500',
  DEF: 'bg-blue-500',
  MID: 'bg-emerald-500',
  FWD: 'bg-red-500',
}

const REASON_STYLE = {
  prediction:   'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20',
  fixture:      'bg-blue-500/10 text-blue-300 border border-blue-500/20',
  form:         'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20',
  injury:       'bg-red-500/10 text-red-300 border border-red-500/20',
  differential: 'bg-purple-500/10 text-purple-300 border border-purple-500/20',
}

// ─── FPL Shirt SVG (team-colored) ─────────────────────────────────────────────

function Shirt({ color, size = 'md' }) {
  const sz = size === 'lg' ? 'w-14 h-14' : size === 'sm' ? 'w-8 h-8' : 'w-11 h-11'
  return (
    <svg viewBox="0 0 120 95" className={`${sz} drop-shadow-md`}>
      <path d="M30,8 L8,30 L24,37 L24,88 L96,88 L96,37 L112,30 L90,8 Q75,1 60,11 Q45,1 30,8Z"
        fill={color} stroke="rgba(255,255,255,0.25)" strokeWidth="2"/>
      <path d="M30,8 L8,30 L24,37 L30,24Z"  fill="rgba(0,0,0,0.18)"/>
      <path d="M90,8 L112,30 L96,37 L90,24Z" fill="rgba(0,0,0,0.18)"/>
      <path d="M46,13 Q60,23 74,13 Q68,8 60,10 Q52,8 46,13Z" fill="rgba(255,255,255,0.35)"/>
    </svg>
  )
}

// ─── Player Card ───────────────────────────────────────────────────────────────

const STATUS_WARN = { d: '⚠', i: '✕', s: '🟠' }

function PlayerCard({ p }) {
  const pos   = p.position_name
  const color = getTeamColor(p.team_short)
  const warn  = STATUS_WARN[p.status]

  return (
    <div className="flex flex-col items-center w-[58px] sm:w-[74px] md:w-[90px] select-none">
      {/* Captain / VC crown above card */}
      <div className="h-5 flex items-center justify-center mb-0.5">
        {p.is_captain && (
          <Crown className="w-4 h-4 text-yellow-400 fill-yellow-400 drop-shadow-sm" />
        )}
        {!p.is_captain && p.is_vice_captain && (
          <Crown className="w-3.5 h-3.5 text-slate-300 fill-slate-300" />
        )}
      </div>

      <motion.div
        whileHover={{ y: -4, scale: 1.02 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        className="w-full bg-white/90 dark:bg-[#0f172a]/90 backdrop-blur-md border border-slate-200 dark:border-white/10 rounded-xl overflow-hidden shadow-lg hover:border-cyan-500/30 hover:shadow-cyan-500/20 transition-all"
      >
        {/* Position color bar */}
        <div className={`h-1 w-full ${POS_BAR_COLOR[pos] || 'bg-slate-500'}`} />

        {/* Player photo */}
        <div className="relative h-9 sm:h-[50px] md:h-[62px]">
          <PlayerPhotoCard
            code={p.photo_code}
            name={p.web_name}
            pos={pos}
            height="100%"
          />
          {/* Team colour underline */}
          <div className="absolute bottom-0 left-0 right-0 h-[2px]" style={{ backgroundColor: color }} />
          {/* Status warning badge */}
          {warn && (
            <span className="absolute top-1 left-1 text-[10px] text-yellow-400 drop-shadow">{warn}</span>
          )}
        </div>

        <div className="px-1.5 pt-1.5 pb-1.5 flex flex-col gap-1">
          {/* Name */}
          <p className="text-slate-900 dark:text-white text-[10px] font-semibold truncate leading-tight text-center">
            {p.web_name}
          </p>

          {/* Price + form */}
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-slate-500 dark:text-slate-400">£{p.sell_price?.toFixed(1)}m</span>
            <span className="flex items-center gap-0.5 bg-cyan-500/10 text-cyan-400 text-[9px] px-1 py-0.5 rounded">
              <Zap className="w-2 h-2" />
              {p.form ?? '—'}
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

function PitchRow({ players }) {
  if (!players?.length) return null
  return (
    <div className="flex justify-center items-start gap-1 sm:gap-2 md:gap-8 flex-wrap">
      {players.map(p => <PlayerCard key={p.id} p={p} />)}
    </div>
  )
}

function SquadPitch({ xi, bench, totalPoints }) {
  const gk  = xi.filter(p => p.position_name === 'GK')
  const def = xi.filter(p => p.position_name === 'DEF')
  const mid = xi.filter(p => p.position_name === 'MID')
  const fwd = xi.filter(p => p.position_name === 'FWD')
  const benchGk  = bench.filter(p => p.position_name === 'GK')
  const benchOut = bench.filter(p => p.position_name !== 'GK').sort((a, b) => (a.bench_order || 0) - (b.bench_order || 0))
  const benchLabels = ['GKP', '1st', '2nd', '3rd']

  return (
    <div className="rounded-3xl p-4 md:p-6" style={{ background: '#1a002e', border: '1px solid rgba(0,255,135,0.1)' }}>
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">Predicted Squad</h2>
        {totalPoints != null && (
          <span className="flex items-center gap-1 bg-cyan-500/10 text-cyan-400 text-xs px-2.5 py-1 rounded-full">
            <Zap className="w-3 h-3" />
            {totalPoints} pts
          </span>
        )}
      </div>

      {/* Pitch */}
      <div className="relative rounded-2xl overflow-hidden" style={{ border: '1px solid rgba(0,255,135,0.12)' }}>
        <PitchSVG />

        <div className="relative z-10 px-2 md:px-4 pt-6 pb-6 space-y-4 md:space-y-5">
          <PitchRow players={gk} />
          <PitchRow players={def} />
          <PitchRow players={mid} />
          <PitchRow players={fwd} />
        </div>
      </div>

      {/* Bench */}
      <div className="border-t border-slate-200/50 dark:border-white/5 pt-4 mt-4">
        <p className="text-center text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-widest mb-3">Bench</p>
        <div className="flex justify-center gap-1 sm:gap-2 md:gap-4 flex-wrap">
          {[...benchGk, ...benchOut].map((p, i) => (
            <div key={p.id} className="flex flex-col items-center gap-1">
              <PlayerCard p={p} />
              <span className="bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 text-[9px] uppercase tracking-widest px-2 py-0.5 rounded-full">
                {benchLabels[i] || ''}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Captain Panel ─────────────────────────────────────────────────────────────

function CaptainPanel({ captainSuggestion, onGenerate, isPending, hasSquad }) {
  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-3xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
          <Crown className="w-4 h-4 text-yellow-400 fill-yellow-400" />
          Captain Pick
        </h2>
        {hasSquad && (
          <button
            onClick={onGenerate}
            disabled={isPending}
            className="text-sm flex items-center gap-1.5 disabled:opacity-50 transition-colors font-semibold" style={{ color: '#00ff87' }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isPending ? 'animate-spin' : ''}`} />
            {isPending ? 'Generating…' : 'Generate'}
          </button>
        )}
      </div>

      {captainSuggestion ? (
        <div className="space-y-2">
          {/* Captain row */}
          <div className="flex items-center gap-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-3">
            <div className="relative flex-shrink-0">
              <PlayerPhoto
                code={captainSuggestion.captain_photo_code}
                name={captainSuggestion.captain_name}
                pos={captainSuggestion.captain_position || 'MID'}
                size="lg"
              />
              <div className="absolute -bottom-1 -right-1 bg-yellow-400 rounded-full p-0.5">
                <Crown className="w-2.5 h-2.5 text-slate-900 fill-slate-900" />
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-slate-900 dark:text-white text-sm font-semibold truncate leading-tight">{captainSuggestion.captain_name}</p>
              <p className="text-slate-500 dark:text-slate-400 text-xs truncate">{captainSuggestion.captain_team}</p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-yellow-400 text-xs uppercase tracking-widest">Captain</p>
              <p className="text-emerald-400 text-sm font-bold font-mono">{captainSuggestion.captain_predicted?.toFixed(1)}</p>
            </div>
          </div>

          {/* VC row */}
          <div className="flex items-center gap-3 bg-slate-500/10 border border-slate-500/20 rounded-xl p-3">
            <div className="relative flex-shrink-0">
              <PlayerPhoto
                code={captainSuggestion.vc_photo_code}
                name={captainSuggestion.vc_name}
                pos={captainSuggestion.vc_position || 'MID'}
                size="lg"
              />
              <div className="absolute -bottom-1 -right-1 bg-slate-400 rounded-full p-0.5">
                <Crown className="w-2.5 h-2.5 text-slate-900 fill-slate-900" />
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-slate-900 dark:text-white text-sm font-semibold truncate leading-tight">{captainSuggestion.vc_name}</p>
              <p className="text-slate-500 dark:text-slate-400 text-xs truncate">{captainSuggestion.vc_team}</p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-slate-500 dark:text-slate-400 text-xs uppercase tracking-widest">Vice C</p>
              <p className="text-emerald-400 text-sm font-bold font-mono">{captainSuggestion.vc_predicted?.toFixed(1)}</p>
            </div>
          </div>

          {/* Differential row */}
          {captainSuggestion.differential_name && (
            <div className="flex items-center gap-3 bg-purple-500/10 border border-purple-500/20 rounded-xl p-3">
              <PlayerPhoto
                code={captainSuggestion.differential_photo_code}
                name={captainSuggestion.differential_name}
                pos={captainSuggestion.differential_position || 'MID'}
                size="lg"
              />
              <div className="min-w-0 flex-1">
                <p className="text-slate-900 dark:text-white text-sm font-semibold truncate leading-tight">{captainSuggestion.differential_name}</p>
                <p className="text-slate-500 dark:text-slate-400 text-xs truncate">{captainSuggestion.differential_selected?.toFixed(1)}% owned</p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-purple-400 text-xs uppercase tracking-widest flex items-center gap-1">
                  <Zap className="w-2.5 h-2.5" />Diff
                </p>
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="text-slate-600 dark:text-slate-500 text-sm">Sync your squad first, then generate captain picks.</p>
      )}
    </div>
  )
}

// ─── Transfers Panel ───────────────────────────────────────────────────────────

function TransfersPanel({ transfers, onRefresh, isPending, hasSquad }) {
  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-3xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
          <ArrowRightLeft className="w-4 h-4 text-emerald-400" />
          Transfer Suggestions
        </h2>
        {hasSquad && (
          <button
            onClick={onRefresh}
            disabled={isPending}
            className="text-sm flex items-center gap-1.5 disabled:opacity-50 transition-colors font-semibold" style={{ color: '#00ff87' }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isPending ? 'animate-spin' : ''}`} />
            {isPending ? 'Analysing…' : 'Refresh'}
          </button>
        )}
      </div>

      {transfers?.length > 0 ? (
        <div className="space-y-3">
          {transfers.map(t => (
            <div
              key={t.id}
              className="bg-slate-50 dark:bg-white/[0.02] border border-slate-200/50 dark:border-white/5 rounded-xl p-3 space-y-2"
            >
              {/* Out row */}
              <div className="flex items-center gap-2">
                <ArrowDownRight className="w-4 h-4 text-red-400 flex-shrink-0" />
                <PlayerPhoto
                  code={t.player_out_photo_code}
                  name={t.player_out_name}
                  pos={t.player_out_position?.slice(0,3).toUpperCase() || 'MID'}
                  size="sm"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-red-400 text-sm font-semibold truncate leading-tight">{t.player_out_name}</p>
                  <p className="text-slate-600 dark:text-slate-500 text-[10px]">{t.player_out_team} · £{t.player_out_price?.toFixed(1)}m · {t.player_out_form} form</p>
                </div>
              </div>

              {/* In row */}
              <div className="flex items-center gap-2">
                <ArrowUpRight className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <PlayerPhoto
                  code={t.player_in_photo_code}
                  name={t.player_in_name}
                  pos={t.player_in_position?.slice(0,3).toUpperCase() || 'MID'}
                  size="sm"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-emerald-400 text-sm font-semibold truncate leading-tight">{t.player_in_name}</p>
                  <p className="text-slate-600 dark:text-slate-500 text-[10px]">{t.player_in_team} · £{t.player_in_price?.toFixed(1)}m · {t.player_in_form} form</p>
                </div>
              </div>

              {/* Bottom row */}
              <div className="flex items-center justify-between pt-1 border-t border-slate-200/50 dark:border-white/5">
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium capitalize ${REASON_STYLE[t.reason] || REASON_STYLE.differential}`}>
                  {t.reason}
                </span>
                <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs px-2 py-0.5 rounded-full font-mono font-semibold">
                  +{t.points_gain?.toFixed(2)} pts
                </span>
              </div>
            </div>
          ))}

          <Link
            to="/advice"
            className="flex items-center justify-center gap-1.5 text-sm pt-1 transition-colors font-semibold" style={{ color: '#00ff87' }}
          >
            View All <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <p className="text-slate-600 dark:text-slate-500 text-sm">
          {hasSquad
            ? 'Click Refresh to generate suggestions.'
            : 'Sync your squad first to see transfer suggestions.'}
        </p>
      )}
    </div>
  )
}

// ─── Dashboard ─────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user } = useAuth()
  const qc = useQueryClient()

  const { data: dash, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => getDashboard().then(r => r.data),
  })

  const syncMut = useMutation({
    mutationFn: syncSquad,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard'] }),
  })
  const transferMut = useMutation({
    mutationFn: generateTransfers,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard'] }),
  })
  const captainMut = useMutation({
    mutationFn: generateCaptain,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard'] }),
  })

  if (isLoading) return (
    <div className="flex items-center justify-center h-full" style={{ background: '#0d001a' }}>
      <p className="animate-pulse text-lg font-display" style={{ color: 'rgba(0,255,135,0.5)' }}>Loading dashboard…</p>
    </div>
  )

  const { current_gameweek, squad, transfer_suggestions, captain_suggestion } = dash || {}

  const kpis = [
    { label: 'GW Points',     value: squad?.gameweek_points ?? '—', icon: Target,    color: 'text-purple-400',  border: 'border-purple-500/20' },
    { label: 'Season Points', value: squad?.total_points    ?? '—', icon: Trophy,    color: 'text-yellow-400',  border: 'border-yellow-500/20' },
    { label: 'Team Value',    value: squad?.total_value ? `£${squad.total_value.toFixed(1)}m` : '—', icon: TrendingUp, color: 'text-cyan-400',    border: 'border-cyan-500/20'   },
    { label: 'In Bank',       value: squad?.bank ? `£${squad.bank.toFixed(1)}m` : '—', icon: Wallet, color: 'text-emerald-400', border: 'border-emerald-500/20' },
  ]

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-8">

      {/* Sticky header */}
      <div className="h-16 flex items-center justify-between px-4 md:px-8 backdrop-blur-xl sticky top-0 z-40 -mx-4 md:-mx-8 -mt-4 md:-mt-8 mb-0"
        style={{ borderBottom: '1px solid rgba(0,255,135,0.1)', background: 'rgba(13,0,26,0.9)' }}>
        <div className="flex items-center gap-3">
          <h1 className="text-base font-bold text-slate-900 dark:text-white">
            {current_gameweek || 'Dashboard'}
          </h1>
          <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full uppercase tracking-widest font-semibold">
            Active
          </span>
        </div>
        {user?.fpl_team_id && (
          <button
            onClick={() => syncMut.mutate()}
            disabled={syncMut.isPending}
            className="flex items-center gap-2 disabled:opacity-50 px-4 py-2 rounded-xl text-sm font-bold transition-all"
          style={{ background: '#00ff87', color: '#0d001a', boxShadow: '0 0 20px -6px rgba(0,255,135,0.45)' }}
          >
            <RefreshCw className={`w-4 h-4 ${syncMut.isPending ? 'animate-spin' : ''}`} />
            {syncMut.isPending ? 'Syncing…' : 'Sync Squad'}
          </button>
        )}
      </div>

      {/* KPI Cards */}
      {squad ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {kpis.map((kpi, i) => (
            <motion.div
              key={kpi.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`border ${kpi.border} rounded-2xl p-5 flex items-center gap-4`}
              style={{ background: '#1a002e' }}
            >
              <div className={`p-3 rounded-xl bg-slate-100 dark:bg-white/5 ${kpi.color}`}>
                <kpi.icon className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">{kpi.label}</p>
                <p className="text-base md:text-3xl font-bold text-slate-900 dark:text-white font-mono leading-tight">{kpi.value}</p>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="border border-dashed rounded-2xl p-8 text-center" style={{ background: '#1a002e', borderColor: 'rgba(0,255,135,0.15)' }}>
          <p className="text-slate-600 dark:text-slate-500">No squad synced yet.</p>
          {user?.fpl_team_id
            ? <button onClick={() => syncMut.mutate()} className="mt-3 text-cyan-400 hover:text-cyan-300 text-sm transition-colors">Sync your squad →</button>
            : <Link to="/profile" className="mt-3 inline-block text-yellow-400 hover:text-yellow-300 text-sm transition-colors">Add your FPL Team ID in Profile settings →</Link>
          }
        </div>
      )}

      {/* Main grid: pitch + side panel */}
      {squad?.players?.length > 0 ? (() => {
        const toCard = sp => ({
          id:              sp.id,
          position_name:   sp.player.position_name,
          web_name:        sp.player.web_name,
          is_captain:      sp.is_captain,
          is_vice_captain: sp.is_vice_captain,
          status:          sp.player.status || 'a',
          sell_price:      sp.sell_price,
          team_short:      sp.player.team_short || sp.player.team_name,
          form:            sp.player.form,
          bench_order:     sp.bench_order,
          photo_code:      sp.player.code,
        })
        const xi    = squad.players.filter(sp =>  sp.is_starter).map(toCard)
        const bench = squad.players.filter(sp => !sp.is_starter).map(toCard)

        return (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Pitch — 2 cols */}
            <div className="lg:col-span-2">
              <SquadPitch xi={xi} bench={bench} totalPoints={squad.total_points} />
            </div>

            {/* Side panel — 1 col */}
            <div className="space-y-6">
              <CaptainPanel
                captainSuggestion={captain_suggestion}
                onGenerate={() => captainMut.mutate()}
                isPending={captainMut.isPending}
                hasSquad={!!squad}
              />
              <TransfersPanel
                transfers={transfer_suggestions}
                onRefresh={() => transferMut.mutate()}
                isPending={transferMut.isPending}
                hasSquad={!!squad}
              />
            </div>
          </div>
        )
      })() : (
        /* No squad state */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 bg-white dark:bg-[#0f172a] border border-dashed border-slate-200 dark:border-white/10 rounded-3xl p-12 flex flex-col items-center justify-center text-center gap-3">
            <p className="text-slate-500 dark:text-slate-400 text-lg">No squad data yet.</p>
            <p className="text-slate-700 dark:text-slate-600 text-sm">
              {user?.fpl_team_id
                ? 'Click Sync Squad to load your team.'
                : <><Link to="/profile" className="text-yellow-400 hover:text-yellow-300 transition-colors">Add your FPL Team ID</Link> in Profile settings first.</>
              }
            </p>
          </div>

          <div className="space-y-6">
            <CaptainPanel
              captainSuggestion={captain_suggestion}
              onGenerate={() => captainMut.mutate()}
              isPending={captainMut.isPending}
              hasSquad={false}
            />
            <TransfersPanel
              transfers={transfer_suggestions}
              onRefresh={() => transferMut.mutate()}
              isPending={transferMut.isPending}
              hasSquad={false}
            />
          </div>
        </div>
      )}
    </div>
  )
}
