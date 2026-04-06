import { useQuery } from '@tanstack/react-query'
import { Sparkles, TrendingDown, TrendingUp, AlertTriangle, CheckCircle, Crown, Zap, ArrowRight, Shuffle, Repeat2, LayoutGrid, Wand2 } from 'lucide-react'
import { getAdvice } from '../api/fpl'
import { getTeamColor } from '../theme/teamColors'
import { cn } from '../lib/utils'
import PlayerPhoto, { PlayerPhotoCard } from '../components/PlayerPhoto'
import PitchSVG from '../components/PitchSVG'

const AI_PITCH_ORDER = ['GK', 'DEF', 'MID', 'FWD']

const RISK_CONFIG = {
  safe: { label: 'Safe', className: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' },
  differential: { label: 'Differential', className: 'bg-amber-500/20 text-amber-400 border border-amber-500/30' },
  avoid: { label: 'Avoid', className: 'bg-red-500/20 text-red-400 border border-red-500/30' },
}

const POS_BAR_COLOR = {
  GK:  'bg-yellow-500',
  DEF: 'bg-blue-500',
  MID: 'bg-emerald-500',
  FWD: 'bg-red-500',
}

function AIPitchCard({ player, isCaptain, isViceCaptain }) {
  const adj   = player.adjusted_points ?? player.predicted_points
  const color = getTeamColor(player.team)
  const dt    = player.dream_team_appearances ?? 0

  return (
    <div className="flex flex-col items-center w-[58px] sm:w-[74px] md:w-[90px] select-none">
      {/* Crown above card */}
      <div className="h-5 flex items-center justify-center mb-0.5">
        {isCaptain && <Crown className="w-4 h-4 text-yellow-400 fill-yellow-400 drop-shadow-sm" />}
        {!isCaptain && isViceCaptain && <Crown className="w-3.5 h-3.5 text-slate-300 fill-slate-300" />}
      </div>
      <div className="w-full bg-white/90 dark:bg-[#0f172a]/90 backdrop-blur-md border border-slate-200 dark:border-white/10 rounded-xl overflow-hidden shadow-lg hover:border-cyan-500/30 hover:shadow-cyan-500/20 transition-all">
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

function PitchSkeleton() {
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
    </div>
  )
}

function TransferAdviceCard({ advice }) {
  const { transfer_out, transfer_in, budget_after, risk_level, reasoning } = advice
  const risk = RISK_CONFIG[risk_level] || RISK_CONFIG.safe

  if (!transfer_out && !transfer_in) {
    return (
      <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Transfer Advice</h2>
        <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-5 py-4">
          <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <p className="text-emerald-400 font-semibold">No transfer recommended this gameweek</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Transfer Advice</h2>
        <span className={cn('text-xs font-semibold px-2.5 py-1 rounded-full', risk.className)}>
          {risk.label}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Transfer Out */}
        <div className="border-l-4 border-red-500 bg-red-500/5 rounded-r-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-red-400">Transfer Out</span>
          </div>
          {transfer_out ? (
            <>
              <p className="font-bold text-slate-900 dark:text-white text-base">{transfer_out.name}</p>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{transfer_out.reason}</p>
            </>
          ) : (
            <p className="text-slate-500 dark:text-slate-400 text-sm italic">None specified</p>
          )}
        </div>

        {/* Transfer In */}
        <div className="border-l-4 border-emerald-500 bg-emerald-500/5 rounded-r-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Transfer In</span>
          </div>
          {transfer_in ? (
            <>
              <p className="font-bold text-slate-900 dark:text-white text-base">{transfer_in.name}</p>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{transfer_in.reason}</p>
            </>
          ) : (
            <p className="text-slate-500 dark:text-slate-400 text-sm italic">None specified</p>
          )}
        </div>
      </div>

      {typeof budget_after === 'number' && (
        <p className="text-sm text-slate-500 dark:text-slate-400 font-mono">
          Budget remaining after transfer:{' '}
          <span className="text-cyan-400 font-bold">£{budget_after.toFixed(1)}m</span>
        </p>
      )}

      {reasoning && (
        <blockquote className="border-l-4 border-slate-200 dark:border-white/10 border-slate-200 dark:border-white/10 pl-4 text-slate-500 dark:text-slate-400 text-sm leading-relaxed italic bg-slate-100 dark:bg-white/5 rounded-r-xl py-3 pr-4">
          {reasoning}
        </blockquote>
      )}
    </div>
  )
}

function BestXIPitch({ bestXi }) {
  const { starting_xi, bench, captain, vice_captain } = bestXi

  const gk  = starting_xi.filter(p => p.position === 'GK')
  const def = starting_xi.filter(p => p.position === 'DEF')
  const mid = starting_xi.filter(p => p.position === 'MID')
  const fwd = starting_xi.filter(p => p.position === 'FWD')

  const benchGk  = (bench || []).filter(p => p.position === 'GK')
  const benchOut = (bench || []).filter(p => p.position !== 'GK')
  const benchLabels = ['GKP', '1st', '2nd', '3rd']

  const isCapt = (p) => captain && captain.id === p.id
  const isVc   = (p) => vice_captain && vice_captain.id === p.id

  const formation = [def.length, mid.length, fwd.length].join('-')
  const totalPts  = starting_xi.reduce((s, p) => s + (p.adjusted_points ?? p.predicted_points ?? 0), 0)

  const PitchRow = ({ players }) => (
    <div className="flex justify-center items-start gap-1 sm:gap-2 md:gap-6 flex-wrap">
      {players.map(p => <AIPitchCard key={p.id} player={p} isCaptain={isCapt(p)} isViceCaptain={isVc(p)} />)}
    </div>
  )

  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-3xl p-4 md:p-6">
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Best XI</h2>
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
          <PitchRow players={gk} />
          <PitchRow players={def} />
          <PitchRow players={mid} />
          <PitchRow players={fwd} />
        </div>
      </div>

      {/* Bench */}
      {bench && bench.length > 0 && (
        <div className="border-t border-slate-200/50 dark:border-white/5 pt-4 mt-4">
          <p className="text-center text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-widest mb-3">Bench</p>
          <div className="flex justify-center gap-1 sm:gap-2 md:gap-4 flex-wrap">
            {[...benchGk, ...benchOut].map((p, i) => (
              <div key={p.id} className="flex flex-col items-center gap-1">
                <AIPitchCard player={p} isCaptain={false} isViceCaptain={false} />
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

const CHIP_CONFIG = {
  bench_boost:    { label: 'Bench Boost',    icon: LayoutGrid,  color: 'text-purple-400',  bg: 'bg-purple-500/10',  border: 'border-purple-500/25'  },
  triple_captain: { label: 'Triple Captain', icon: Crown,       color: 'text-yellow-400',  bg: 'bg-yellow-500/10',  border: 'border-yellow-500/25'  },
  free_hit:       { label: 'Free Hit',       icon: Wand2,       color: 'text-cyan-400',    bg: 'bg-cyan-500/10',    border: 'border-cyan-500/25'    },
  wildcard:       { label: 'Wildcard',       icon: Shuffle,     color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/25' },
}

const CONFIDENCE_STYLE = {
  high:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  medium: 'bg-amber-500/15   text-amber-400   border-amber-500/30',
  low:    'bg-slate-500/15   text-slate-500 dark:text-slate-400   border-slate-500/30',
}

function ChipAdviceSection({ chips }) {
  const keys = ['bench_boost', 'triple_captain', 'free_hit', 'wildcard']
  const available = keys.filter(k => chips[k])
  if (!available.length) return null

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Repeat2 className="w-5 h-5 text-cyan-400" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Chip Advice</h2>
        <span className="text-xs text-slate-600 dark:text-slate-500 ml-1">Should you use a chip this gameweek?</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {available.map(key => {
          const chip = chips[key]
          const cfg  = CHIP_CONFIG[key]
          const Icon = cfg.icon
          const rec  = chip.recommended
          return (
            <div key={key} className={cn('bg-white dark:bg-[#0f172a] border rounded-2xl p-5', cfg.border)}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-2">
                  <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', cfg.bg)}>
                    <Icon className={cn('w-4 h-4', cfg.color)} />
                  </div>
                  <span className={cn('font-bold text-sm', cfg.color)}>{cfg.label}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className={cn(
                    'text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider',
                    CONFIDENCE_STYLE[chip.confidence] || CONFIDENCE_STYLE.low
                  )}>
                    {chip.confidence}
                  </span>
                  <span className={cn(
                    'text-xs font-bold px-2.5 py-1 rounded-full border',
                    rec
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                      : 'bg-red-500/10 text-red-400 border-red-500/20'
                  )}>
                    {rec ? '✓ Use it' : '✗ Hold'}
                  </span>
                </div>
              </div>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">{chip.reasoning}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Advice() {
  const {
    data: advice,
    isLoading,
    isError,
    isFetching,
    refetch,
    isFetched,
  } = useQuery({
    queryKey: ['advice'],
    queryFn: () => getAdvice().then(r => r.data),
    enabled: false,
    staleTime: 1000 * 60 * 30,
    gcTime: 1000 * 60 * 60,
  })

  const showSkeleton = isLoading || isFetching

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <header className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-cyan-400" />
            AI Advice
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            Powered by Llama 3.3 70B via Groq
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className={cn(
            'flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all',
            isFetching
              ? 'bg-cyan-600/50 text-slate-900 dark:text-white/60 cursor-not-allowed'
              : 'bg-cyan-600 hover:bg-cyan-500 text-slate-900 dark:text-white shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30'
          )}
        >
          <Sparkles className={cn('w-4 h-4', isFetching && 'animate-spin')} />
          {isFetching ? 'Analysing...' : 'Get AI Advice'}
        </button>
      </header>

      {/* Error state */}
      {isError && !isFetching && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-5 py-4">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-red-400 font-medium">Advisor unavailable — try again later</p>
        </div>
      )}

      {/* Not yet fetched — prompt state */}
      {!isFetched && !showSkeleton && !isError && (
        <div className="bg-white dark:bg-[#0f172a] border border-dashed border-slate-200 dark:border-white/10 rounded-2xl p-16 text-center">
          <Sparkles className="w-12 h-12 text-cyan-400/40 mx-auto mb-4" />
          <p className="text-slate-500 dark:text-slate-400 text-lg font-medium">
            Click "Get AI Advice" to analyse your squad
          </p>
          <p className="text-slate-600 dark:text-slate-500 text-sm mt-2">
            AI will suggest your best XI, captain pick, transfer advice, substitution reasoning, and chip recommendations
          </p>
        </div>
      )}

      {/* Loading skeleton */}
      {showSkeleton && (
        <div className="space-y-8">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="h-5 w-32 bg-slate-200 dark:bg-white/10 rounded animate-pulse" />
            </div>
            <PitchSkeleton />
            <p className="text-center text-slate-500 dark:text-slate-400 text-sm animate-pulse">
              Analysing your squad with AI...
            </p>
          </div>
          <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-6 space-y-4">
            <div className="h-5 w-40 bg-slate-200 dark:bg-white/10 rounded animate-pulse" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="h-28 bg-slate-100 dark:bg-white/5 rounded-xl animate-pulse" />
              <div className="h-28 bg-slate-100 dark:bg-white/5 rounded-xl animate-pulse" />
            </div>
            <div className="h-16 bg-slate-100 dark:bg-white/5 rounded-xl animate-pulse" />
          </div>
        </div>
      )}

      {/* Results */}
      {advice && !showSkeleton && (
        <>
          {/* Section 1 - Best XI */}
          <div className="space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">AI Best XI</h2>
              <div className="flex items-center gap-2">
                {advice.xi_reasoning?.team_rating && (
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                    advice.xi_reasoning.team_rating === 'strong'  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                    advice.xi_reasoning.team_rating === 'risky'   ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                                                                     'bg-amber-500/20 text-amber-400 border-amber-500/30'
                  }`}>{advice.xi_reasoning.team_rating}</span>
                )}
                {advice.best_xi?.formation && (
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/5 px-2.5 py-1 rounded-full">
                    {advice.best_xi.formation.replace(/^1-/, '')}
                  </span>
                )}
              </div>
            </div>

            {advice.best_xi && <BestXIPitch bestXi={advice.best_xi} />}

            {/* Overall comment */}
            {advice.xi_reasoning?.overall_comment && (
              <div className="bg-white/3 border border-slate-200 dark:border-white/8 rounded-xl px-4 py-3">
                <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">{advice.xi_reasoning.overall_comment}</p>
              </div>
            )}

            {/* Captain reasoning */}
            {advice.xi_reasoning?.captain_reasoning && (
              <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl px-4 py-3 flex gap-3">
                <Crown className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-yellow-400 text-xs font-bold uppercase tracking-wider mb-1">Captain pick</p>
                  <p className="text-slate-300 text-sm leading-relaxed">{advice.xi_reasoning.captain_reasoning}</p>
                </div>
              </div>
            )}

            {/* Suggested substitutions */}
            {advice.xi_reasoning?.swaps?.length > 0 && (
              <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Suggested Substitutions</h3>
                </div>
                {advice.xi_reasoning.swaps.map((s, i) => (
                  <div key={i} className="bg-white/3 border border-slate-200 dark:border-white/8 rounded-xl p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="bg-red-500/15 text-red-400 border border-red-500/30 text-xs font-bold px-2.5 py-1 rounded-full">
                        OUT: {s.out}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-600 dark:text-slate-500 flex-shrink-0" />
                      <span className="bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-bold px-2.5 py-1 rounded-full">
                        IN: {s.in}
                      </span>
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">{s.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2 - Transfer Advice */}
          {advice.transfer_advice && (
            <TransferAdviceCard advice={advice.transfer_advice} />
          )}

          {/* Section 3 - Chip Advice */}
          {advice.xi_reasoning?.chip_advice && (
            <ChipAdviceSection chips={advice.xi_reasoning.chip_advice} />
          )}
        </>
      )}
    </div>
  )
}
