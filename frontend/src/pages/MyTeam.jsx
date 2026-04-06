import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getSquad, syncSquad, getChips, getAdvice } from '../api/fpl'
import { useAuth } from '../context/AuthContext'
import { RefreshCw, Star, Sparkles, AlertTriangle, TrendingDown, TrendingUp, CheckCircle, Crown, Zap } from 'lucide-react'
import { getTeamColor } from '../theme/teamColors'
import { cn } from '../lib/utils'
import PlayerPhoto, { PlayerPhotoCard } from '../components/PlayerPhoto'
import PitchSVG from '../components/PitchSVG'

const POS_ORDER = ['GK', 'DEF', 'MID', 'FWD']
const AI_PITCH_ORDER = ['GK', 'DEF', 'MID', 'FWD']

const POS_BAR_COLOR = {
  GK:  'bg-yellow-500',
  DEF: 'bg-blue-500',
  MID: 'bg-emerald-500',
  FWD: 'bg-red-500',
}

const RISK_CONFIG = {
  safe: { label: 'Safe', className: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' },
  differential: { label: 'Differential', className: 'bg-amber-500/20 text-amber-400 border border-amber-500/30' },
  avoid: { label: 'Avoid', className: 'bg-red-500/20 text-red-400 border border-red-500/30' },
}

const STATUS_WARN = { d: '⚠', i: '✕', s: '🟠' }

// Squad player card — matches Dashboard PlayerCard design
function FPLPlayerCard({ sp }) {
  const pos   = sp.player.position_name
  const color = getTeamColor(sp.player.team_name)
  const warn  = STATUS_WARN[sp.player.status]
  return (
    <div className={cn('flex flex-col items-center w-[58px] sm:w-[74px] md:w-[90px] select-none', !sp.is_starter && 'opacity-60')}>
      {/* Crown above */}
      <div className="h-5 flex items-center justify-center mb-0.5">
        {sp.is_captain && <Crown className="w-4 h-4 text-yellow-400 fill-yellow-400 drop-shadow-sm" />}
        {!sp.is_captain && sp.is_vice_captain && <Crown className="w-3.5 h-3.5 text-slate-300 fill-slate-300" />}
      </div>
      <div className="w-full bg-white/90 dark:bg-[#0f172a]/90 backdrop-blur-md border border-slate-200 dark:border-white/10 rounded-xl overflow-hidden shadow-lg hover:border-cyan-500/30 hover:shadow-cyan-500/20 transition-all">
        {/* Position colour bar */}
        <div className={`h-1 w-full ${POS_BAR_COLOR[pos] || 'bg-slate-500'}`} />
        {/* Photo */}
        <div className="relative h-9 sm:h-[50px] md:h-[62px]">
          <PlayerPhotoCard code={sp.player.code} name={sp.player.web_name} pos={pos} height="100%" />
          <div className="absolute bottom-0 left-0 right-0 h-[2px]" style={{ backgroundColor: color }} />
          {warn && <span className="absolute top-1 left-1 text-[10px] text-yellow-400 drop-shadow">{warn}</span>}
        </div>
        {/* Info */}
        <div className="px-1.5 pt-1.5 pb-1.5 flex flex-col gap-1">
          <p className="text-slate-900 dark:text-white text-[10px] font-semibold truncate leading-tight text-center">{sp.player.web_name}</p>
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-slate-500 dark:text-slate-400">£{sp.sell_price?.toFixed(1)}m</span>
            <span className="flex items-center gap-0.5 bg-cyan-500/10 text-cyan-400 text-[9px] px-1 py-0.5 rounded">
              <Zap className="w-2 h-2" />
              {sp.player.form ?? '—'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Pitch layout — matches Dashboard SquadPitch design
function FPLPitch({ starters, bench, gwPoints }) {
  const byPos = POS_ORDER.reduce((acc, p) => {
    acc[p] = starters.filter(sp => sp.player.position_name === p)
    return acc
  }, {})
  const benchGk  = bench.filter(sp => sp.player.position_name === 'GK')
  const benchOut = bench.filter(sp => sp.player.position_name !== 'GK')
    .sort((a, b) => (a.bench_order || 0) - (b.bench_order || 0))
  const benchLabels = ['GKP', '1st', '2nd', '3rd']
  const formation = ['DEF','MID','FWD'].map(p => byPos[p]?.length || 0).join('-')

  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-3xl p-4 md:p-6">
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">My Squad</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{formation}</p>
        </div>
        {gwPoints != null && (
          <span className="flex items-center gap-1 bg-cyan-500/10 text-cyan-400 text-xs px-2.5 py-1 rounded-full">
            <Zap className="w-3 h-3" />
            {gwPoints} pts
          </span>
        )}
      </div>
      {/* Pitch */}
      <div className="relative border-2 border-slate-200 dark:border-white/10 rounded-2xl overflow-hidden">
        <PitchSVG />
        <div className="relative z-10 px-2 md:px-4 pt-6 pb-6 space-y-4 md:space-y-5">
          {POS_ORDER.map(pos => byPos[pos]?.length > 0 && (
            <div key={pos} className="flex justify-center items-start gap-1 sm:gap-2 md:gap-8 flex-wrap">
              {byPos[pos].map(sp => <FPLPlayerCard key={sp.id} sp={sp} />)}
            </div>
          ))}
        </div>
      </div>
      {/* Bench */}
      <div className="border-t border-slate-200/50 dark:border-white/5 pt-4 mt-4">
        <p className="text-center text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-widest mb-3">Bench</p>
        <div className="flex justify-center gap-1 sm:gap-2 md:gap-4 flex-wrap">
          {[...benchGk, ...benchOut].map((sp, i) => (
            <div key={sp.id} className="flex flex-col items-center gap-1">
              <FPLPlayerCard sp={sp} />
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


function AIPitchCard({ player, isCaptain, isViceCaptain, wasStarterInSquad, wasOnBenchInSquad, isInStartingXI }) {
  const movedToStarting = isInStartingXI && wasOnBenchInSquad
  const movedToBench    = !isInStartingXI && wasStarterInSquad
  const adj   = player.adjusted_points ?? player.predicted_points
  const color = getTeamColor(player.team)
  const dt    = player.dream_team_appearances ?? 0

  const tooltip = movedToStarting ? 'AI moved to starting XI' : movedToBench ? 'AI moved to bench' : undefined

  return (
    <div className={cn('flex flex-col items-center w-[58px] sm:w-[74px] md:w-[90px] select-none', movedToBench && 'opacity-60')} title={tooltip}>
      {/* Crown above */}
      <div className="h-5 flex items-center justify-center mb-0.5">
        {isCaptain && <Crown className="w-4 h-4 text-yellow-400 fill-yellow-400 drop-shadow-sm" />}
        {!isCaptain && isViceCaptain && <Crown className="w-3.5 h-3.5 text-slate-300 fill-slate-300" />}
      </div>
      <div className={cn(
        'w-full bg-white/90 dark:bg-[#0f172a]/90 backdrop-blur-md border border-slate-200 dark:border-white/10 rounded-xl overflow-hidden shadow-lg hover:border-cyan-500/30 transition-all',
        movedToStarting && 'ring-2 ring-green-500 shadow-green-500/30 shadow-lg',
        movedToBench    && 'ring-2 ring-red-500 shadow-red-500/30 shadow-lg',
      )}>
        {/* Position colour bar */}
        <div className={`h-1 w-full ${POS_BAR_COLOR[player.position] || 'bg-slate-500'}`} />
        {/* Photo */}
        <div className="relative h-9 sm:h-[50px] md:h-[62px]">
          <PlayerPhotoCard code={player.photo_code} name={player.name} pos={player.position} height="100%" />
          <div className="absolute bottom-0 left-0 right-0 h-[2px]" style={{ backgroundColor: color }} />
        </div>
        {/* Info */}
        <div className="px-1.5 pt-1.5 pb-1.5 flex flex-col gap-1">
          <p className="text-slate-900 dark:text-white text-[10px] font-semibold truncate leading-tight text-center">{player.name}</p>
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-slate-500 dark:text-slate-400">£{player.price?.toFixed(1)}m</span>
            <span className="flex items-center gap-0.5 bg-cyan-500/10 text-cyan-400 text-[9px] px-1 py-0.5 rounded">
              <Zap className="w-2 h-2" />
              {typeof adj === 'number' ? adj.toFixed(1) : adj}
            </span>
          </div>
          {dt > 0 && <p className="text-yellow-300 text-[9px] text-center leading-none">⭐×{dt}</p>}
        </div>
      </div>
    </div>
  )
}

function AIPitchSkeleton() {
  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(180deg, #1a5c35 0%, #1e6b3e 100%)' }}>
      <div className="p-6 space-y-6">
        <div className="text-center">
          <div className="h-4 w-16 bg-white/20 rounded animate-pulse mx-auto" />
        </div>
        {[3, 3, 4, 1].map((count, i) => (
          <div key={i} className="flex gap-3 justify-center">
            {Array.from({ length: count }).map((_, j) => (
              <div key={j} className="w-20 h-24 bg-slate-200 dark:bg-white/10 rounded-xl animate-pulse" />
            ))}
          </div>
        ))}
      </div>
      <div className="bg-black/20 px-6 py-4 flex gap-3 justify-center">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="w-20 h-24 bg-slate-200 dark:bg-white/10 rounded-xl animate-pulse" />
        ))}
      </div>
      <p className="text-center text-slate-900 dark:text-white/50 text-sm pb-4 animate-pulse">
        Analysing your squad with AI...
      </p>
    </div>
  )
}

function AIPitch({ bestXi, squadPlayers }) {
  const { starting_xi, bench, captain, vice_captain } = bestXi

  // Build dual-key map for glow logic
  const squadMap = (squadPlayers || []).reduce((acc, sp) => {
    if (sp.player.fpl_id != null) acc[sp.player.fpl_id] = sp
    if (sp.player.id != null) acc[sp.player.id] = sp
    return acc
  }, {})

  const startingIds = new Set(starting_xi.map(p => p.id))

  const gk  = starting_xi.filter(p => p.position === 'GK')
  const def = starting_xi.filter(p => p.position === 'DEF')
  const mid = starting_xi.filter(p => p.position === 'MID')
  const fwd = starting_xi.filter(p => p.position === 'FWD')

  const benchGk  = (bench || []).filter(p => p.position === 'GK')
  const benchOut = (bench || []).filter(p => p.position !== 'GK')
  const benchLabels = ['GKP', '1st', '2nd', '3rd']

  const formation = [def.length, mid.length, fwd.length].join('-')
  const totalPts  = starting_xi.reduce((s, p) => s + (p.adjusted_points ?? p.predicted_points ?? 0), 0)

  const renderCard = (player, inStarting) => {
    const sp = squadMap[player.id]
    const wasStarterInSquad = sp ? sp.is_starter : null
    const wasOnBenchInSquad = sp ? !sp.is_starter : null
    return (
      <AIPitchCard
        key={player.id}
        player={player}
        isCaptain={captain && captain.id === player.id}
        isViceCaptain={vice_captain && vice_captain.id === player.id}
        wasStarterInSquad={wasStarterInSquad}
        wasOnBenchInSquad={wasOnBenchInSquad}
        isInStartingXI={inStarting}
      />
    )
  }

  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-3xl p-4 md:p-6">
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">AI Best XI</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{formation}</p>
        </div>
        <span className="flex items-center gap-1 bg-cyan-500/10 text-cyan-400 text-xs px-2.5 py-1 rounded-full">
          <Zap className="w-3 h-3" />
          {totalPts.toFixed(1)} pts
        </span>
      </div>
      {/* Pitch */}
      <div className="relative border-2 border-slate-200 dark:border-white/10 rounded-2xl overflow-hidden">
        <PitchSVG />
        <div className="relative z-10 px-2 md:px-4 pt-6 pb-6 space-y-4 md:space-y-5">
          <div className="flex justify-center items-start gap-1 sm:gap-2 md:gap-4 flex-wrap">{gk.map(p => renderCard(p, startingIds.has(p.id)))}</div>
          <div className="flex justify-center items-start gap-1 sm:gap-2 md:gap-4 flex-wrap">{def.map(p => renderCard(p, startingIds.has(p.id)))}</div>
          <div className="flex justify-center items-start gap-1 sm:gap-2 md:gap-4 flex-wrap">{mid.map(p => renderCard(p, startingIds.has(p.id)))}</div>
          <div className="flex justify-center items-start gap-1 sm:gap-2 md:gap-4 flex-wrap">{fwd.map(p => renderCard(p, startingIds.has(p.id)))}</div>
        </div>
      </div>
      {/* Bench */}
      {bench && bench.length > 0 && (
        <div className="border-t border-slate-200/50 dark:border-white/5 pt-4 mt-4">
          <p className="text-center text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-widest mb-3">Bench</p>
          <div className="flex justify-center gap-1 sm:gap-2 md:gap-4 flex-wrap">
            {[...benchGk, ...benchOut].map((player, i) => (
              <div key={player.id} className="flex flex-col items-center gap-1">
                {renderCard(player, false)}
                <span className="bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 text-[9px] uppercase tracking-widest px-2 py-0.5 rounded-full">
                  {benchLabels[i] || ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TransferStrip({ advice }) {
  const { transfer_out, transfer_in, risk_level } = advice
  const risk = RISK_CONFIG[risk_level] || RISK_CONFIG.safe

  if (!transfer_out && !transfer_in) {
    return (
      <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-5 py-3">
        <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
        <p className="text-emerald-400 font-medium text-sm">No transfer needed this gameweek</p>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3 flex-wrap bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl px-5 py-3 text-sm">
      {transfer_out && (
        <span className="flex items-center gap-1.5 text-red-400 font-medium">
          <TrendingDown className="w-4 h-4" />
          OUT: <span className="font-bold">{transfer_out.name}</span>
        </span>
      )}
      {transfer_out && transfer_in && (
        <span className="text-slate-600 dark:text-slate-500">→</span>
      )}
      {transfer_in && (
        <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
          <TrendingUp className="w-4 h-4" />
          IN: <span className="font-bold">{transfer_in.name}</span>
        </span>
      )}
      <span className={cn('ml-auto text-xs font-semibold px-2.5 py-1 rounded-full', risk.className)}>
        {risk.label}
      </span>
    </div>
  )
}

export default function MyTeam() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [mode, setMode] = useState('squad')

  const { data: squad, isLoading } = useQuery({
    queryKey: ['squad'],
    queryFn: () => getSquad().then(r => r.data),
  })

  const { data: chips } = useQuery({
    queryKey: ['chips'],
    queryFn: () => getChips().then(r => r.data),
  })

  const {
    data: advice,
    isLoading: adviceLoading,
    isError: adviceError,
  } = useQuery({
    queryKey: ['advice'],
    queryFn: () => getAdvice().then(r => r.data),
    staleTime: 1000 * 60 * 5,
    enabled: true,
  })

  const syncMut = useMutation({
    mutationFn: syncSquad,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['squad'] }),
  })

  if (isLoading) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-slate-500 dark:text-slate-400 animate-pulse">Loading team...</div>
    </div>
  )

  if (!squad) return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <header>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
          <Star className="w-8 h-8 text-cyan-400" />
          My Team
        </h1>
      </header>
      <div className="bg-white dark:bg-[#0f172a] border border-dashed border-slate-200 dark:border-white/10 rounded-xl p-12 text-center">
        <p className="text-slate-300 text-lg font-semibold">No squad synced yet</p>
        {user?.fpl_team_id ? (
          <button
            onClick={() => syncMut.mutate()}
            disabled={syncMut.isPending}
            className="mt-4 bg-cyan-600 hover:bg-cyan-500 text-slate-900 dark:text-white px-6 py-2.5 rounded-xl transition-colors flex items-center gap-2 mx-auto"
          >
            <RefreshCw className={cn('w-4 h-4', syncMut.isPending && 'animate-spin')} />
            {syncMut.isPending ? 'Syncing...' : 'Sync from FPL'}
          </button>
        ) : (
          <Link to="/profile" className="mt-3 inline-block text-yellow-400 hover:text-yellow-300 text-sm">
            Set your FPL Team ID in Profile →
          </Link>
        )}
      </div>
    </div>
  )

  const starters = (squad.players || []).filter(sp => sp.is_starter)
  const bench = (squad.players || []).filter(sp => !sp.is_starter).sort((a, b) => (a.bench_order || 0) - (b.bench_order || 0))
  const byPos = POS_ORDER.reduce((acc, p) => {
    acc[p] = starters.filter(sp => sp.player.position_name === p)
    return acc
  }, {})

  const kpis = [
    { label: 'GW Points', value: squad.gameweek_points, color: 'text-purple-400' },
    { label: 'Season Pts', value: squad.total_points, color: 'text-yellow-400' },
    { label: 'Team Value', value: `£${squad.squad_value?.toFixed(1)}m`, color: 'text-cyan-400' },
    { label: 'Overall Rank', value: squad.overall_rank?.toLocaleString(), color: 'text-emerald-400' },
  ]

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <header className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
            <Star className="w-8 h-8 text-cyan-400" />
            My Team
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {squad.gameweek_name} · {squad.free_transfers} free transfer{squad.free_transfers !== 1 ? 's' : ''} · £{squad.bank?.toFixed(1)}m bank
          </p>
        </div>
        {user?.fpl_team_id && (
          <button
            onClick={() => syncMut.mutate()}
            disabled={syncMut.isPending}
            className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-slate-900 dark:text-white px-5 py-2.5 rounded-xl text-sm transition-colors"
          >
            <RefreshCw className={cn('w-4 h-4', syncMut.isPending && 'animate-spin')} />
            {syncMut.isPending ? 'Syncing...' : 'Refresh'}
          </button>
        )}
      </header>

      {/* Mode toggle */}
      <div className="flex items-center gap-1 bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-1 w-fit">
        <button
          onClick={() => setMode('squad')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
            mode === 'squad'
              ? 'bg-slate-200 dark:bg-white/10 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          )}
        >
          <Star className="w-4 h-4" />
          My Squad
        </button>
        <button
          onClick={() => setMode('ai')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
            mode === 'ai'
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          )}
        >
          <Sparkles className="w-4 h-4" />
          AI Best XI
        </button>
      </div>

      {/* KPI Cards (always visible) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map(({ label, value, color }) => (
          <div key={label} className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-4 text-center min-w-0">
            <p className="text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider mb-1">{label}</p>
            <p className={cn('text-sm md:text-2xl font-bold font-mono', color)}>{value ?? '—'}</p>
          </div>
        ))}
      </div>

      {/* Squad mode */}
      {mode === 'squad' && (
        <>
          {/* Pitch layout */}
          <FPLPitch starters={starters} bench={bench} gwPoints={squad.gameweek_points} />

          {chips?.length > 0 && (
            <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-6">
              <h3 className="font-semibold mb-4 text-slate-900 dark:text-white">Chip Advice</h3>
              <div className="grid grid-cols-2 gap-4">
                {chips.map(c => (
                  <div key={c.id} className={cn(
                    'border rounded-xl p-4',
                    c.recommended
                      ? 'border-cyan-500/30 bg-cyan-500/5'
                      : 'border-slate-200 dark:border-white/8'
                  )}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium capitalize text-slate-900 dark:text-white">
                        {c.chip.replace('_', ' ')}
                      </span>
                      {c.recommended && (
                        <span className="text-xs bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded">Recommended</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/10 rounded-full">
                        <div className="h-1.5 bg-cyan-500 rounded-full" style={{ width: `${(c.score / 10) * 100}%` }} />
                      </div>
                      <span className="text-sm text-slate-500 dark:text-slate-400 font-mono">{c.score?.toFixed(1)}/10</span>
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 text-sm">{c.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* AI Best XI mode */}
      {mode === 'ai' && (
        <>
          {/* AI advisor error — fall back with warning */}
          {adviceError && (
            <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/20 rounded-xl px-5 py-4 mb-2">
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
              <p className="text-amber-400 font-medium text-sm">
                AI advisor unavailable — showing your current squad
              </p>
            </div>
          )}

          {/* Loading skeleton */}
          {adviceLoading && !adviceError && (
            <AIPitchSkeleton />
          )}

          {/* AI pitch when data available (or show squad pitch on error) */}
          {!adviceLoading && (
            <>
              {advice?.best_xi && !adviceError ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h2 className="text-base font-semibold text-slate-900 dark:text-white">AI Best XI</h2>
                    <div className="flex items-center gap-2">
                      {advice.xi_reasoning?.team_rating && (
                        <span className={cn(
                          'text-xs font-semibold px-2.5 py-1 rounded-full border',
                          advice.xi_reasoning.team_rating === 'strong' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                          advice.xi_reasoning.team_rating === 'risky'  ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                                                                          'bg-amber-500/20 text-amber-400 border-amber-500/30'
                        )}>{advice.xi_reasoning.team_rating}</span>
                      )}
                      {advice.best_xi.formation && (
                        <span className="text-xs font-mono text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/5 px-2.5 py-1 rounded-full">
                          {(f => f?.replace(/^\d+-/, '') ?? '4-3-3')(advice.best_xi.formation)}
                        </span>
                      )}
                    </div>
                  </div>

                  <AIPitch bestXi={advice.best_xi} squadPlayers={squad.players} />

                  {/* Groq swap suggestions */}
                  {advice.xi_reasoning?.swaps?.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 space-y-2">
                      <p className="text-amber-400 text-xs font-bold uppercase tracking-wider">AI suggests</p>
                      {advice.xi_reasoning.swaps.map((s, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm flex-wrap">
                          <span className="text-red-400 font-medium">{s.out}</span>
                          <span className="text-slate-500 dark:text-slate-400">→</span>
                          <span className="text-emerald-400 font-medium">{s.in}</span>
                          <span className="text-slate-500 dark:text-slate-400 text-xs">— {s.reason}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Captain reasoning */}
                  {advice.xi_reasoning?.captain_reasoning && (
                    <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl px-4 py-3">
                      <p className="text-yellow-400 text-xs font-bold uppercase tracking-wider mb-1">Captain reasoning</p>
                      <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                        {advice.xi_reasoning.captain_reasoning}
                      </p>
                    </div>
                  )}

                  {/* Transfer advice strip */}
                  {advice.transfer_advice && (
                    <TransferStrip advice={advice.transfer_advice} />
                  )}
                </div>
              ) : (
                /* Fallback to squad pitch on error or no advice */
                <FPLPitch starters={starters} bench={bench} gwPoints={squad.gameweek_points} />
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
