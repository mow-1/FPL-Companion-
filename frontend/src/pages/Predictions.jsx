import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { getBestPicks, getBestTeam, getTrackRecord, getCurrentGw, getGwHistory, getGwDetail, getDifferentials, getCommunityCompare } from '../api/fpl'
import { Zap, Crown, Trophy, Wallet, TrendingUp, Target } from 'lucide-react'
import { getTeamColor } from '../theme/teamColors'
import PlayerPhoto, { PlayerPhotoCard } from '../components/PlayerPhoto'

// ─── constants ────────────────────────────────────────────────────────────────

const POS_BADGE = {
  GK:  'bg-[#F0A500]/20 text-yellow-300 border-[#F0A500]/40',
  DEF: 'bg-blue-400/20  text-blue-300  border-blue-400/40',
  MID: 'bg-cyan-400/20  text-cyan-300  border-cyan-400/40',
  FWD: 'bg-red-400/20   text-red-300   border-red-400/40',
}

const JERSEY = {
  GK:  { body: '#e8d44d', sleeve: '#c9b600', collar: '#fff' },
  DEF: { body: '#3b82f6', sleeve: '#1d4ed8', collar: '#fff' },
  MID: { body: '#22c55e', sleeve: '#15803d', collar: '#fff' },
  FWD: { body: '#ef4444', sleeve: '#b91c1c', collar: '#fff' },
}

const STATUS_ICON  = { a: null, d: '⚠', i: '✕', s: '🟠', u: '✕' }
const STATUS_COLOR = { d: 'text-yellow-400', i: 'text-red-400', s: 'text-orange-400' }

// ─── Player card ──────────────────────────────────────────────────────────────

const POS_BAR  = { GK: 'bg-yellow-500', DEF: 'bg-blue-500', MID: 'bg-emerald-500', FWD: 'bg-red-500' }
const POS_TEXT = { GK: 'text-yellow-400', DEF: 'text-blue-400', MID: 'text-emerald-400', FWD: 'text-red-400' }

function PlayerCard({ p, showActual = false }) {
  const pos    = p.position_name
  const status = p.status || 'a'
  const warn   = STATUS_ICON[status]
  const teamColor = getTeamColor(p.team_short)
  const displayActual = showActual && p.actual_points != null
    ? (p.is_captain ? p.actual_points * 2 : p.actual_points)
    : null

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.02 }}
      className="relative w-[88px] cursor-pointer select-none"
    >
      {p.is_captain && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 z-20 drop-shadow-[0_0_8px_rgba(250,204,21,0.7)]">
          <Crown className="w-4 h-4 text-yellow-400 fill-yellow-400" />
        </div>
      )}
      {!p.is_captain && p.is_vice_captain && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 z-20 drop-shadow-[0_0_6px_rgba(203,213,225,0.5)]">
          <Crown className="w-3.5 h-3.5 text-slate-300 fill-slate-300" />
        </div>
      )}
      {warn && (
        <span className={`absolute top-8 left-1 z-20 text-[10px] ${STATUS_COLOR[status] || 'text-slate-500 dark:text-slate-400'}`}>{warn}</span>
      )}

      <div className="bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-md border border-slate-200 dark:border-white/10 rounded-xl overflow-hidden shadow-lg transition-all hover:border-cyan-500/30 hover:shadow-[0_4px_20px_-4px_rgba(6,182,212,0.2)]">
        {/* Position colour bar */}
        <div className={`h-1 w-full ${POS_BAR[pos] || 'bg-slate-500'}`} />

        {/* Player photo */}
        <div className="relative">
          <PlayerPhotoCard
            code={p.photo_code}
            name={p.web_name}
            pos={pos}
            height={64}
          />
          {/* Team colour strip at bottom of photo */}
          <div
            className="absolute bottom-0 left-0 right-0 h-[3px]"
            style={{ backgroundColor: teamColor }}
          />
        </div>

        <div className="px-1.5 pt-1.5 pb-1.5">
          {/* Name */}
          <p className="text-slate-900 dark:text-white text-[10px] font-bold truncate leading-tight text-center mb-1">
            {p.web_name}
          </p>

          {/* Points */}
          {displayActual != null ? (
            <div className="flex items-center justify-center gap-1 mb-1">
              <span className="text-slate-600 dark:text-slate-500 text-[9px]">{p.predicted_points?.toFixed(1)}</span>
              <span className="text-slate-700 dark:text-slate-600 text-[9px]">→</span>
              <span className={`text-[10px] font-bold ${displayActual >= Math.round(p.predicted_points) ? 'text-emerald-400' : 'text-orange-400'}`}>
                {displayActual}
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-0.5 bg-cyan-500/10 px-1 py-0.5 rounded mb-1">
              <Zap className="w-2.5 h-2.5 text-cyan-400" />
              <span className="text-[10px] font-semibold text-cyan-400">{p.predicted_points?.toFixed(1)}</span>
            </div>
          )}

          {/* Fixture chip */}
          <div className="bg-slate-100 dark:bg-white/5 rounded px-1 py-0.5 text-center">
            <p className={`text-[9px] font-medium truncate ${POS_TEXT[pos] || 'text-slate-500 dark:text-slate-400'}`}>
              {p.fixture || 'TBC'}
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── Pitch ────────────────────────────────────────────────────────────────────

function PitchRow({ players, showActual }) {
  if (!players?.length) return null
  return (
    <div className="flex justify-center items-start gap-2 flex-wrap">
      {players.map((p, i) => <PlayerCard key={`${p.fpl_id}-${i}-${p.position}`} p={p} showActual={showActual} />)}
    </div>
  )
}

function Pitch({ xi, bench, formation, showActual = false }) {
  const gk  = xi.filter(p => p.position_name === 'GK')
  const def = xi.filter(p => p.position_name === 'DEF')
  const mid = xi.filter(p => p.position_name === 'MID')
  const fwd = xi.filter(p => p.position_name === 'FWD')
  const benchGk  = bench.filter(p => p.position_name === 'GK')
  const benchOut = bench.filter(p => p.position_name !== 'GK').sort((a,b)=>(a.bench_order||0)-(b.bench_order||0))
  const benchLabels = ['GKP', '1st', '2nd', '3rd']

  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-3xl p-3 md:p-5 shadow-xl">
      {/* Pitch field */}
      <div
        className="relative rounded-2xl border-2 border-slate-200 dark:border-white/10 overflow-hidden py-6 md:py-8"
        style={{
          background: '#1b4332',
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 10%, rgba(0,0,0,0.07) 10%, rgba(0,0,0,0.07) 20%)',
        }}
      >
        {/* Pitch markings */}
        <div className="absolute inset-0 pointer-events-none opacity-25">
          <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-white" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 md:w-36 md:h-36 rounded-full border-2 border-white" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-56 md:w-72 h-20 md:h-28 border-x-2 border-b-2 border-white" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-20 md:w-28 h-8 md:h-10 border-x-2 border-b-2 border-white" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-56 md:w-72 h-20 md:h-28 border-x-2 border-t-2 border-white" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-20 md:w-28 h-8 md:h-10 border-x-2 border-t-2 border-white" />
        </div>

        {formation && (
          <div className="absolute top-2 right-3 z-10 bg-black/50 text-slate-900 dark:text-white/80 text-xs px-2.5 py-0.5 rounded-full font-medium">
            {formation}
          </div>
        )}

        <div className="relative z-10 space-y-4 md:space-y-5">
          <PitchRow players={gk}  showActual={showActual} />
          <PitchRow players={def} showActual={showActual} />
          <PitchRow players={mid} showActual={showActual} />
          <PitchRow players={fwd} showActual={showActual} />
        </div>
      </div>

      {/* Bench */}
      <div className="mt-4 pt-4 border-t border-slate-200/50 dark:border-white/5">
        <p className="text-center text-slate-600 dark:text-slate-500 text-xs uppercase tracking-widest mb-3">Bench</p>
        <div className="flex justify-center gap-3 md:gap-6 flex-wrap">
          {[...benchGk, ...benchOut].map((p, i) => (
            <div key={p.fpl_id} className="flex flex-col items-center gap-1">
              <span className="text-[9px] font-medium text-slate-600 dark:text-slate-500 uppercase tracking-widest bg-slate-100 dark:bg-white/5 px-2 py-0.5 rounded border border-slate-200/50 dark:border-white/5">
                {benchLabels[i] || ''}
              </span>
              <PlayerCard p={p} showActual={showActual} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Best Team tab ────────────────────────────────────────────────────────────

const KPI_META = [
  { key: 'formation',         label: 'Formation',    icon: Target,    color: 'text-slate-900 dark:text-white',        border: 'border-slate-200 dark:border-white/10',        bg: 'bg-slate-100 dark:bg-white/5'         },
  { key: 'total_cost',        label: 'Total Cost',   icon: Wallet,    color: 'text-yellow-400',   border: 'border-yellow-500/25',   bg: 'bg-yellow-500/5'    },
  { key: 'remaining_budget',  label: 'In Bank',      icon: TrendingUp,color: 'text-cyan-400',     border: 'border-cyan-500/25',     bg: 'bg-cyan-500/5'      },
  { key: 'xi_predicted_pts',  label: 'Pred. XI Pts', icon: Zap,       color: 'text-blue-400',     border: 'border-blue-500/25',     bg: 'bg-blue-500/5'      },
  { key: 'gameweek',          label: 'Gameweek',     icon: Trophy,    color: 'text-emerald-400',  border: 'border-emerald-500/25',  bg: 'bg-emerald-500/5'   },
]

function BestTeamTab() {
  const [budget, setBudget] = useState(100)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['best-team', budget],
    queryFn: () => getBestTeam(budget).then(r => r.data),
  })
  const { data: trackData, isLoading: trackLoading } = useQuery({
    queryKey: ['track-record'],
    queryFn: () => getTrackRecord(3).then(r => r.data),
    staleTime: 1000 * 60 * 10,
  })
  const hasTrack = Array.isArray(trackData) && trackData.length > 0 && trackData[0].xi?.length > 0

  const maxPts = data ? Math.max(...[...( data.xi || []), ...(data.bench || [])].map(p => p.predicted_points || 0), 1) : 1

  return (
    <div className="space-y-6">

      {/* ── Controls bar ── */}
      <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-2xl p-5 flex flex-wrap gap-6 items-center">
        <div className="flex-1 min-w-56">
          <label className="block text-sm text-slate-500 dark:text-slate-400 mb-2">
            Budget: <span className="text-cyan-400 font-bold">£{budget}m</span>
          </label>
          <input type="range" min={80} max={120} step={0.5} value={budget}
            onChange={e => setBudget(Number(e.target.value))}
            className="w-full accent-cyan-500 h-1.5 rounded-full" />
          <div className="flex justify-between text-xs text-slate-700 dark:text-slate-600 mt-1"><span>£80m</span><span>£120m</span></div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {[['GK','bg-yellow-500'],['DEF','bg-blue-500'],['MID','bg-emerald-500'],['FWD','bg-red-500']].map(([l,c])=>(
            <span key={l} className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/8 rounded-lg text-xs text-slate-500 dark:text-slate-400">
              <span className={`w-2 h-2 rounded-full ${c}`}/>{l}
            </span>
          ))}
          <span className="text-xs text-slate-700 dark:text-slate-600 self-center ml-1">2GK · 5DEF · 5MID · 3FWD · max 3/club</span>
        </div>
      </div>

      {/* ── KPI cards ── */}
      {data && !isFetching && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {KPI_META.map(({ key, label, icon: Icon, color, border, bg }, i) => {
            const raw = data[key]
            const value = key === 'total_cost' ? `£${raw}m`
                        : key === 'remaining_budget' ? `£${raw}m`
                        : key === 'xi_predicted_pts' ? raw?.toFixed(1)
                        : raw
            return (
              <motion.div key={key}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                className={`bg-white dark:bg-[#0f172a] border ${border} rounded-2xl p-4 flex items-center gap-3`}
              >
                <div className={`w-9 h-9 rounded-xl ${bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-4 h-4 ${color}`} />
                </div>
                <div>
                  <p className="text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-wider mb-0.5">{label}</p>
                  <p className={`text-lg font-bold font-mono ${color}`}>{value ?? '—'}</p>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}

      {/* ── Captain / VC ── */}
      {data && !isFetching && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white dark:bg-[#0f172a] border border-yellow-500/25 rounded-2xl p-4 flex items-center gap-3">
            <div className="relative flex-shrink-0">
              <PlayerPhoto
                code={data.captain_photo_code}
                name={data.captain}
                pos={data.captain_position || 'MID'}
                size="xl"
              />
              <div className="absolute -bottom-1 -right-1 bg-yellow-400 rounded-full p-0.5 shadow-lg shadow-yellow-500/30">
                <Crown className="w-3 h-3 text-slate-900 fill-slate-900" />
              </div>
            </div>
            <div className="min-w-0">
              <p className="text-yellow-400 text-xs uppercase tracking-wider font-semibold mb-0.5">Captain</p>
              <p className="text-slate-900 dark:text-white font-bold text-lg leading-tight truncate">{data.captain}</p>
              <p className="text-slate-600 dark:text-slate-500 text-xs mt-0.5">Points doubled this GW</p>
            </div>
          </div>
          <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/10 rounded-2xl p-4 flex items-center gap-3">
            <div className="relative flex-shrink-0">
              <PlayerPhoto
                code={data.vc_photo_code}
                name={data.vice_captain}
                pos={data.vc_position || 'MID'}
                size="xl"
              />
              <div className="absolute -bottom-1 -right-1 bg-slate-400 rounded-full p-0.5 shadow">
                <Crown className="w-3 h-3 text-slate-900 fill-slate-900" />
              </div>
            </div>
            <div className="min-w-0">
              <p className="text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider font-semibold mb-0.5">Vice Captain</p>
              <p className="text-slate-900 dark:text-white font-bold text-lg leading-tight truncate">{data.vice_captain}</p>
              <p className="text-slate-600 dark:text-slate-500 text-xs mt-0.5">Backup if captain can't play</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Pitch ── */}
      {isLoading || isFetching
        ? (
          <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-3xl flex items-center justify-center h-64">
            <p className="text-slate-600 dark:text-slate-500 animate-pulse text-sm">Building best team…</p>
          </div>
        )
        : data?.xi?.length > 0 && <Pitch xi={data.xi} bench={data.bench} formation={data.formation} />
      }

      {/* ── Squad table ── */}
      {data?.squad?.length > 0 && !isFetching && (
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200/50 dark:border-white/5">
            <h3 className="font-bold text-slate-900 dark:text-white">Full Squad</h3>
            <p className="text-slate-600 dark:text-slate-500 text-xs mt-0.5">15 players · bench rows dimmed</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-slate-600 dark:text-slate-500 text-xs uppercase border-b border-slate-200/50 dark:border-white/5">
                <tr>
                  {['Pos','Player','Club','Price','Predicted','Confidence','Role'].map(h=>(
                    <th key={h} className="px-4 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {[...data.xi, ...data.bench].map(p => {
                  const teamColor = getTeamColor(p.team_short)
                  const confPct   = Math.round(Math.min((p.predicted_points / maxPts) * 100, 100))
                  const confColor = confPct >= 70 ? 'bg-emerald-500' : confPct >= 45 ? 'bg-cyan-500' : 'bg-slate-500'
                  return (
                    <tr key={p.fpl_id}
                      className={`transition-colors hover:bg-white/[0.03] ${!p.is_starter ? 'opacity-40' : ''}`}>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded border font-medium ${POS_BADGE[p.position_name]}`}>
                          {p.position_name}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: teamColor }} />
                          <span className="font-semibold text-slate-900 dark:text-white">{p.web_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400 font-mono text-xs">{p.team_short}</td>
                      <td className="px-4 py-3 text-yellow-400 font-mono">£{p.price?.toFixed(1)}m</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 bg-cyan-500/10 w-fit px-2 py-0.5 rounded">
                          <Zap className="w-3 h-3 text-cyan-400" />
                          <span className="text-cyan-400 font-semibold font-mono text-xs">{p.predicted_points?.toFixed(1)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 min-w-32">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${confColor}`} style={{ width: `${confPct}%` }} />
                          </div>
                          <span className="text-[10px] text-slate-600 dark:text-slate-500 font-mono w-8">{confPct}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {p.is_captain
                          ? <span className="inline-flex items-center gap-1 text-xs bg-yellow-400/15 text-yellow-400 border border-yellow-500/25 px-2 py-0.5 rounded-full font-medium">
                              <Crown className="w-3 h-3 fill-yellow-400" /> Captain
                            </span>
                          : p.is_vice_captain
                          ? <span className="inline-flex items-center gap-1 text-xs bg-slate-400/10 text-slate-300 border border-slate-500/20 px-2 py-0.5 rounded-full">
                              <Crown className="w-3 h-3 fill-slate-300" /> Vice-C
                            </span>
                          : !p.is_starter
                          ? <span className="text-xs text-slate-700 dark:text-slate-600">Bench {p.bench_order}</span>
                          : <span className="text-xs text-slate-700 dark:text-slate-600">Starter</span>
                        }
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot className="bg-white/[0.03] border-t border-slate-200/50 dark:border-white/5 text-xs text-slate-600 dark:text-slate-500">
                <tr>
                  <td colSpan={3} className="px-4 py-3 font-medium text-slate-500 dark:text-slate-400">Total (XI)</td>
                  <td className="px-4 py-3 text-yellow-400 font-bold font-mono">£{data.total_cost}m</td>
                  <td className="px-4 py-3 text-cyan-400 font-bold font-mono">{data.xi_predicted_pts?.toFixed(1)}</td>
                  <td colSpan={2} className="px-4 py-3 text-slate-600 dark:text-slate-500">Bank: <span className="text-cyan-400 font-mono">£{data.remaining_budget}m</span></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* ── Track Record ── */}
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">Model Track Record <span className="text-slate-600 dark:text-slate-500 font-normal text-base">— Last 3 GWs</span></h3>
          <p className="text-slate-600 dark:text-slate-500 text-sm mt-0.5">Predicted vs actual · adaptive learning applied</p>
        </div>

        {trackLoading && (
          <div className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-2xl flex items-center justify-center h-24">
            <p className="text-slate-600 dark:text-slate-500 animate-pulse text-sm">Loading…</p>
          </div>
        )}
        {!trackLoading && !hasTrack && (
          <div className="bg-white dark:bg-[#0f172a] border border-dashed border-slate-200 dark:border-white/10 rounded-2xl p-8 text-center">
            <p className="text-slate-500 dark:text-slate-400">Track record will appear once GW stats are synced.</p>
            <p className="text-slate-700 dark:text-slate-600 text-sm mt-1 font-mono">python manage.py sync_fpl --players</p>
          </div>
        )}

        {hasTrack && trackData.map((rec, i) => {
          const diff   = (rec.actual_pts ?? 0) - (rec.predicted_pts ?? 0)
          const isGood = diff >= 0
          return (
            <motion.div key={rec.gameweek_id || i}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="bg-white dark:bg-[#0f172a] border border-slate-200/50 dark:border-white/5 rounded-2xl overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200/50 dark:border-white/5">
                <div>
                  <h4 className="font-bold text-slate-900 dark:text-white text-lg">{rec.gameweek}</h4>
                  <p className="text-slate-600 dark:text-slate-500 text-xs mt-0.5">Formation: {rec.formation} · C: {rec.captain}</p>
                </div>
                <div className="flex items-center gap-5">
                  <div className="text-center">
                    <p className="text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-wider mb-0.5">Predicted</p>
                    <p className="text-blue-400 font-bold text-2xl font-mono">{rec.predicted_pts?.toFixed(1)}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-wider mb-0.5">Actual</p>
                    <p className={`font-bold text-2xl font-mono ${isGood ? 'text-emerald-400' : 'text-orange-400'}`}>
                      {rec.actual_pts}
                    </p>
                  </div>
                  <div className={`px-3 py-1.5 rounded-xl border text-center ${isGood ? 'bg-emerald-500/10 border-emerald-500/25' : 'bg-orange-500/10 border-orange-500/25'}`}>
                    <p className="text-slate-600 dark:text-slate-500 text-[10px] uppercase tracking-wider mb-0.5">Diff</p>
                    <p className={`font-bold text-lg font-mono ${isGood ? 'text-emerald-400' : 'text-orange-400'}`}>
                      {isGood ? '+' : ''}{diff.toFixed(1)}
                    </p>
                  </div>
                </div>
              </div>
              <div className="p-4">
                <Pitch xi={rec.xi} bench={rec.bench} formation={rec.formation} showActual={true} />
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

// ─── GW History tab ───────────────────────────────────────────────────────────

function DiffBar({ diff }) {
  if (diff == null) return <span className="text-slate-600 dark:text-slate-500 text-xs">Pending</span>
  const abs   = Math.abs(diff)
  const pct   = Math.min(abs / 50, 1) * 100
  const color = diff >= -5 ? 'bg-emerald-500' : diff >= -20 ? 'bg-yellow-500' : 'bg-red-500'
  const label = diff >= 0 ? `+${diff.toFixed(1)}` : diff.toFixed(1)
  const textC = diff >= -5 ? 'text-emerald-400' : diff >= -20 ? 'text-yellow-400' : 'text-red-400'
  return (
    <div className="flex items-center gap-2">
      <span className={`text-xs font-bold w-14 text-right ${textC}`}>{label}</span>
      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function LearningChart({ data }) {
  if (!data?.length) return null
  const maes   = data.map(d => d.mae).filter(Boolean)
  const maxMae = Math.max(...maes, 5)
  const W = 100 / data.length

  return (
    <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-white">Model Learning Curve</h4>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-0.5">Per-player MAE per GW — should trend downward as model calibrates</p>
        </div>
        <div className="flex gap-4 text-xs text-slate-600 dark:text-slate-500">
          <span className="flex items-center gap-1"><span className="w-3 h-1 bg-emerald-500 rounded inline-block"/>Good (&lt;2.2)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-1 bg-yellow-500 rounded inline-block"/>Average</span>
          <span className="flex items-center gap-1"><span className="w-3 h-1 bg-red-500 rounded inline-block"/>Poor (&gt;4)</span>
        </div>
      </div>
      <div className="relative h-40 flex items-end gap-px">
        {data.map((d, i) => {
          const mae = d.mae
          if (!mae) {
            return (
              <div key={d.gw} className="flex flex-col items-center justify-end" style={{ width: `${W}%` }}>
                <div className="w-full bg-slate-200 dark:bg-white/10 rounded-t" style={{ height: '4px' }} />
              </div>
            )
          }
          const h   = (mae / maxMae) * 100
          const col = mae < 2.2 ? '#22c55e' : mae < 4 ? '#eab308' : '#ef4444'
          return (
            <div key={d.gw} className="group flex flex-col items-center justify-end relative" style={{ width: `${W}%` }}>
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 hidden group-hover:flex bg-slate-50 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 border-slate-200 dark:border-white/10 rounded px-1.5 py-0.5 text-xs whitespace-nowrap z-10">
                GW{d.gw}: MAE {mae?.toFixed(3)}
              </div>
              <div className="w-full rounded-t transition-all" style={{ height: `${h}%`, background: col }} />
            </div>
          )
        })}
      </div>
      <div className="flex justify-between text-xs text-slate-600 dark:text-slate-500 mt-1">
        <span>GW1</span>
        <span>GW{data[Math.floor(data.length/2)]?.gw || ''}</span>
        <span>GW{data[data.length-1]?.gw || ''}</span>
      </div>
      {maes.length >= 10 && (() => {
        const first5 = maes.slice(0, 5).reduce((a,b)=>a+b,0)/5
        const last5  = maes.slice(-5).reduce((a,b)=>a+b,0)/5
        const improv = ((first5 - last5) / first5 * 100).toFixed(1)
        const improved = last5 < first5
        return (
          <div className={`mt-3 text-center text-xs ${improved ? 'text-emerald-400' : 'text-orange-400'}`}>
            {improved
              ? `MAE improved ${improv}% from first 5 GWs (avg ${first5.toFixed(3)}) to last 5 (avg ${last5.toFixed(3)})`
              : `MAE increased ${Math.abs(improv)}% — model still calibrating`
            }
          </div>
        )
      })()}
    </div>
  )
}

function GwExpandedDetail({ gwId }) {
  const { data, isLoading } = useQuery({
    queryKey: ['gw-detail', gwId],
    queryFn: () => getGwDetail(gwId).then(r => r.data),
    staleTime: Infinity,
  })
  if (isLoading) return <div className="text-slate-500 dark:text-slate-400 animate-pulse text-center py-8 text-sm">Loading squad…</div>
  const rec = data?.[0]
  if (!rec || rec.error) return <div className="text-slate-600 dark:text-slate-500 text-center py-4 text-sm">{rec?.error || 'No data'}</div>
  return (
    <div className="mt-4 space-y-3">
      <Pitch xi={rec.xi || []} bench={rec.bench || []} formation={rec.formation} showActual={rec.has_actual_data} />
    </div>
  )
}

function GwHistoryTab() {
  const [expandedGw, setExpandedGw] = useState(null)
  const [view, setView] = useState('table')
  const [historyView, setHistoryView] = useState('squad')

  const { data: history, isLoading } = useQuery({
    queryKey: ['gw-history'],
    queryFn: () => getGwHistory().then(r => r.data),
    staleTime: 1000 * 60 * 5,
  })

  const rows = Array.isArray(history) ? history : []
  const finished = rows.filter(r => r.has_actual)
  const current  = rows.find(r => !r.has_actual)

  const avg = (arr, field) => {
    const v = arr.map(r => r[field]).filter(x => x != null)
    return v.length ? (v.reduce((a,b)=>a+b,0)/v.length).toFixed(1) : '–'
  }
  const absAvgDiff = (arr) => {
    const v = arr.map(r => r.diff).filter(x => x != null)
    return v.length ? (v.map(Math.abs).reduce((a,b)=>a+b,0)/v.length).toFixed(1) : '–'
  }
  // Prediction bias: avg(actual - predicted) — negative means over-prediction
  const avgBias = (arr) => {
    const v = arr.map(r => r.diff).filter(x => x != null)
    if (!v.length) return null
    return (v.reduce((a,b)=>a+b,0)/v.length)
  }
  const bias = avgBias(finished)

  const avgField = (arr, field) => {
    const v = arr.map(r => r[field]).filter(x => x != null)
    return v.length ? (v.reduce((a,b)=>a+b,0)/v.length) : null
  }
  const avgModelGap = avgField(finished, 'model_gap')
  const avgSquadGap = avgField(finished, 'squad_gap')

  const total = finished.length
  const third = Math.floor(total / 3)
  const phases = [
    { label: 'Early Season', rows: finished.slice(0, third)          },
    { label: 'Mid Season',   rows: finished.slice(third, third * 2)  },
    { label: 'Late Season',  rows: finished.slice(third * 2)         },
  ]

  return (
    <div className="space-y-6">
      {/* Context note */}
      <div className="flex items-start gap-2 bg-white/[0.03] border border-slate-200 dark:border-white/8 rounded-xl px-4 py-3">
        <span className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">ℹ️</span>
        <div className="text-slate-500 dark:text-slate-400 text-xs leading-relaxed space-y-1">
          <p><strong className="text-slate-700">Model Accuracy:</strong> Compares the model's predicted XI score against the theoretical perfect XI (hindsight best picks). Shows pure model error — independent of squad selection.</p>
          <p><strong className="text-slate-700">Squad Performance:</strong> Compares the predicted XI against your actual FPL squad results. The gap here includes both model error AND squad selection constraints.</p>
        </div>
      </div>

      {/* Top summary strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-4 text-center">
          <p className="text-slate-600 dark:text-slate-500 text-xs mb-1">GWs Tracked</p>
          <p className="text-slate-900 dark:text-white font-bold text-2xl font-mono">{finished.length}</p>
        </div>
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-4 text-center">
          <p className="text-slate-600 dark:text-slate-500 text-xs mb-1">Squad Gap (All)</p>
          <p className="text-yellow-400 font-bold text-2xl font-mono">{avgSquadGap != null ? avgSquadGap.toFixed(1) : absAvgDiff(finished)}</p>
          <p className="text-slate-600 dark:text-slate-500 text-[10px] mt-0.5">perfect − actual</p>
        </div>
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-4 text-center">
          <p className="text-slate-600 dark:text-slate-500 text-xs mb-1">Squad Gap (Last 9)</p>
          <p className="text-emerald-400 font-bold text-2xl font-mono">{avgField(finished.slice(-9), 'squad_gap') != null ? avgField(finished.slice(-9), 'squad_gap').toFixed(1) : absAvgDiff(finished.slice(-9))}</p>
          <p className="text-slate-600 dark:text-slate-500 text-[10px] mt-0.5">perfect − actual</p>
        </div>
        <div className="bg-white dark:bg-[#0f172a] border border-cyan-700/30 rounded-xl p-4 text-center">
          <p className="text-slate-600 dark:text-slate-500 text-xs mb-1">Model Accuracy Gap</p>
          {avgModelGap != null ? (
            <>
              <p className="text-cyan-400 font-bold text-2xl font-mono">{avgModelGap.toFixed(1)}</p>
              <p className="text-slate-600 dark:text-slate-500 text-[10px] mt-0.5">perfect − predicted</p>
            </>
          ) : (
            <p className="text-slate-500 dark:text-slate-400 font-bold text-2xl font-mono">–</p>
          )}
        </div>
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-4 text-center">
          <p className="text-slate-600 dark:text-slate-500 text-xs mb-1">Current GW Pred</p>
          <p className="text-blue-400 font-bold text-2xl font-mono">{current?.predicted_pts?.toFixed(1) ?? '–'}</p>
        </div>
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-4 text-center">
          <p className="text-slate-600 dark:text-slate-500 text-xs mb-1">Prediction Bias</p>
          {bias !== null ? (
            <>
              <p className={`font-bold text-2xl font-mono ${bias < 0 ? 'text-orange-400' : 'text-emerald-400'}`}>
                {bias > 0 ? '+' : ''}{bias.toFixed(1)}
              </p>
              <p className="text-slate-600 dark:text-slate-500 text-[10px] mt-0.5">
                {bias < 0 ? 'over-predicts' : 'under-predicts'} avg
              </p>
            </>
          ) : (
            <p className="text-slate-500 dark:text-slate-400 font-bold text-2xl font-mono">–</p>
          )}
        </div>
      </div>

      {/* Phase improvement table */}
      <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-4">
        <h4 className="font-semibold text-sm mb-3 text-slate-700 dark:text-slate-600">Learning Progression by Phase</h4>
        <div className="grid grid-cols-3 gap-3">
          {phases.map((ph, i) => (
            <div key={ph.label} className={`rounded-lg p-3 border ${i===2 ? 'border-cyan-700/50 bg-cyan-900/10' : 'border-slate-200 dark:border-white/10 border-slate-200 dark:border-white/10 bg-slate-50 bg-slate-50 dark:bg-white/[0.02]'}`}>
              <p className="text-slate-500 dark:text-slate-400 text-xs font-medium mb-1">{ph.label}</p>
              <p className="text-slate-900 dark:text-white font-bold">{absAvgDiff(ph.rows)} pts avg diff</p>
              <p className="text-slate-600 dark:text-slate-500 text-xs mt-0.5">MAE: {avg(ph.rows, 'mae')}</p>
              {i===2 && <p className="text-cyan-400 text-xs mt-1 font-medium">Best phase</p>}
            </div>
          ))}
        </div>
      </div>

      {/* View toggles */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1 bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-1">
          {[{k:'squad',l:'Squad Performance'},{k:'model',l:'Model Accuracy'}].map(({k,l})=>(
            <button key={k} onClick={()=>setHistoryView(k)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${historyView===k?'bg-cyan-600 text-slate-900 dark:text-white':'text-slate-500 dark:text-slate-400 hover:text-slate-900'}`}>{l}</button>
          ))}
        </div>
        <div className="flex gap-1 bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-1">
          {[{k:'table',l:'Table'},{k:'chart',l:'Chart'}].map(({k,l})=>(
            <button key={k} onClick={()=>setView(k)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${view===k?'bg-cyan-600 text-slate-900 dark:text-white':'text-slate-500 dark:text-slate-400 hover:text-slate-900'}`}>{l}</button>
          ))}
        </div>
        <span className="text-slate-600 dark:text-slate-500 text-xs">Click any GW row to see the full squad</span>
      </div>

      {isLoading && <div className="text-slate-500 dark:text-slate-400 animate-pulse text-center py-16">Loading GW history…</div>}

      {!isLoading && view === 'chart' && <LearningChart data={finished} />}

      {!isLoading && view === 'table' && (
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 text-xs uppercase sticky top-0">
              <tr>
                {historyView === 'model'
                  ? ['GW','Captain','Formation','Predicted','Perfect (Hindsight)','Model Gap','MAE',''].map(h=>(
                      <th key={h} className="px-4 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                    ))
                  : ['GW','Captain','Formation','Predicted','Actual','Diff','MAE',''].map(h=>(
                      <th key={h} className="px-4 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                    ))
                }
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {current && (
                <tr className="bg-blue-900/20 border-b-2 border-blue-700/30">
                  <td className="px-4 py-3 font-bold text-blue-400">GW{current.gw}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-600">{current.captain || '–'}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{current.formation || '–'}</td>
                  <td className="px-4 py-3 text-blue-400 font-bold font-mono">{current.predicted_pts?.toFixed(1) ?? '–'}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-500">Pending</td>
                  <td className="px-4 py-3" colSpan={2}><span className="text-xs bg-blue-700/40 text-blue-300 px-2 py-0.5 rounded-full">Current GW</span></td>
                  <td className="px-4 py-3">
                    <button onClick={()=>setExpandedGw(expandedGw===current.gw?null:current.gw)}
                      className="text-xs text-slate-500 dark:text-slate-400 transition-colors">
                      {expandedGw===current.gw?'Hide':'View'}
                    </button>
                  </td>
                </tr>
              )}
              {current && expandedGw===current.gw && (
                <tr><td colSpan={8} className="px-4 py-4 bg-white dark:bg-[#0f172a]/60"><GwExpandedDetail gwId={current.gw} /></td></tr>
              )}

              {[...finished].reverse().map(row => {
                const gapVal   = historyView === 'model' ? row.model_gap : row.diff
                const isGood   = gapVal != null && gapVal <= 10
                const isMed    = gapVal != null && gapVal > 10 && gapVal <= 25
                const rowBg    = isGood ? 'hover:bg-emerald-900/10' : isMed ? 'hover:bg-yellow-900/10' : 'hover:bg-red-900/10'
                const expanded = expandedGw === row.gw
                return [
                  <tr key={row.gw} className={`cursor-pointer transition-colors ${rowBg} ${expanded ? 'bg-white/[0.03]' : ''}`}
                    onClick={()=>setExpandedGw(expanded ? null : row.gw)}>
                    <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">GW{row.gw}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-600">{row.captain || '–'}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{row.formation || '–'}</td>
                    <td className="px-4 py-3 text-blue-300 font-mono">{row.predicted_pts?.toFixed(1) ?? '–'}</td>
                    {historyView === 'model' ? (
                      <>
                        <td className="px-4 py-3 font-semibold text-emerald-400 font-mono">{row.perfect_pts?.toFixed(1) ?? '–'}</td>
                        <td className="px-4 py-3 min-w-32">
                          {row.model_gap != null
                            ? <div className="flex items-center gap-2">
                                <span className={`text-xs font-bold w-14 text-right ${row.model_gap <= 10 ? 'text-emerald-400' : row.model_gap <= 25 ? 'text-yellow-400' : 'text-red-400'}`}>{row.model_gap.toFixed(1)}</span>
                                <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                                  <div className={`h-full rounded-full ${row.model_gap <= 10 ? 'bg-emerald-500' : row.model_gap <= 25 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                    style={{ width: `${Math.min(row.model_gap / 50, 1) * 100}%` }} />
                                </div>
                              </div>
                            : <span className="text-slate-600 dark:text-slate-500 text-xs">–</span>
                          }
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white font-mono">{row.actual_pts ?? '–'}</td>
                        <td className="px-4 py-3 min-w-32"><DiffBar diff={row.diff} /></td>
                      </>
                    )}
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs font-mono">{row.mae?.toFixed(3) ?? '–'}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-500 text-xs">{expanded ? '▲' : '▼'}</td>
                  </tr>,
                  expanded && (
                    <tr key={`${row.gw}-detail`}>
                      <td colSpan={8} className="px-4 py-4 bg-white dark:bg-[#0f172a]/60">
                        <GwExpandedDetail gwId={row.gw} />
                      </td>
                    </tr>
                  )
                ]
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Best Picks tab ───────────────────────────────────────────────────────────

const POS_RING = {
  GK:  'border-yellow-500/40 bg-yellow-500/5',
  DEF: 'border-blue-500/40  bg-blue-500/5',
  MID: 'border-cyan-500/40  bg-cyan-500/5',
  FWD: 'border-red-500/40   bg-red-500/5',
}

function PickCard({ pick, rank }) {
  const pos = pick.player_position
  return (
    <div className={`border rounded-xl p-4 ${POS_RING[pos]} ${rank===1?'ring-1 ring-cyan-500/50':''}`}>
      {rank===1 && <div className="text-xs text-cyan-400 font-semibold mb-2">TOP PICK</div>}
      <div className="flex justify-between items-start gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <PlayerPhoto code={pick.player_photo_code} name={pick.player_name} pos={pos} size="lg" />
          <div className="min-w-0">
            <span className={`text-xs px-2 py-0.5 rounded border font-medium ${POS_BADGE[pos]}`}>{pos}</span>
            <p className="font-bold text-base mt-1 text-slate-900 dark:text-white truncate">{pick.player_name}</p>
            <p className="text-slate-500 dark:text-slate-400 text-sm">{pick.player_team} · £{pick.player_price?.toFixed(1)}m</p>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-3xl font-bold text-cyan-400 font-mono">{pick.predicted_points?.toFixed(1)}</p>
          <p className="text-slate-600 dark:text-slate-500 text-xs">pred pts</p>
        </div>
      </div>
      <div className="mt-3 flex gap-3 text-xs text-slate-500 dark:text-slate-400">
        <span>Form <span className="text-slate-900 dark:text-white">{pick.player_form}</span></span>
        <span>Sel <span className="text-slate-900 dark:text-white">{pick.player_selected_by}%</span></span>
        {pick.player_status !== 'a' && <span className="text-yellow-400">⚠ {pick.player_news?.slice(0,30)}</span>}
      </div>
      <p className="text-slate-600 dark:text-slate-500 text-xs mt-2">model: {pick.model_used}</p>
    </div>
  )
}

function BestPicksTab() {
  const [position, setPosition] = useState('')
  const [top, setTop] = useState(10)
  const POSITIONS = [
    { value:'',  label:'All' },
    { value:'1', label:'GK',  color:'text-yellow-400' },
    { value:'2', label:'DEF', color:'text-blue-400' },
    { value:'3', label:'MID', color:'text-cyan-400' },
    { value:'4', label:'FWD', color:'text-red-400' },
  ]
  const { data, isLoading } = useQuery({
    queryKey: ['best-picks', position, top],
    queryFn: () => getBestPicks({ position: position||undefined, top }).then(r=>r.data),
  })
  const picks   = data?.results || data || []
  const grouped = picks.reduce((a,p)=>{ (a[p.player_position]=a[p.player_position]||[]).push(p); return a },{})

  return (
    <div className="space-y-6">
      <div className="flex gap-3 flex-wrap items-center">
        {POSITIONS.map(p=>(
          <button key={p.value} onClick={()=>setPosition(p.value)}
            className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${position===p.value?'bg-slate-200 dark:bg-white/10 border-slate-400 border-white/30 text-slate-900 dark:text-white':'border-slate-200 dark:border-white/10 border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400 hover:text-slate-900'}`}>
            <span className={p.color||''}>{p.label}</span>
          </button>
        ))}
        <select value={top} onChange={e=>setTop(Number(e.target.value))}
          className="ml-auto bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/10 border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500">
          <option value={5}>Top 5</option><option value={10}>Top 10</option><option value={20}>Top 20</option>
        </select>
      </div>
      {isLoading && <div className="text-center text-slate-500 dark:text-slate-400 animate-pulse py-12">Loading…</div>}
      {!isLoading && picks.length===0 && (
        <div className="bg-white dark:bg-[#0f172a] border border-dashed border-slate-200 dark:border-white/10 rounded-xl p-12 text-center text-slate-500 dark:text-slate-400">
          No picks yet — run predictions first.
        </div>
      )}
      {!isLoading && (position
        ? <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {picks.map(p=><PickCard key={p.id} pick={p} rank={p.rank_in_position}/>)}
          </div>
        : ['GK','DEF','MID','FWD'].map(pos=>grouped[pos]?.length?(
            <div key={pos}>
              <h3 className="font-semibold text-slate-700 dark:text-slate-600 mb-3 uppercase tracking-widest text-sm">{pos}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {grouped[pos].map(p=><PickCard key={p.id} pick={p} rank={p.rank_in_position}/>)}
              </div>
            </div>
          ):null)
      )}
    </div>
  )
}

// ─── Edge tab ─────────────────────────────────────────────────────────────────

const FDR_COLOR = { 1:'bg-emerald-500', 2:'bg-emerald-400', 3:'bg-yellow-400', 4:'bg-orange-500', 5:'bg-red-500' }
const FDR_TEXT  = { 1:'FDR 1', 2:'FDR 2', 3:'FDR 3', 4:'FDR 4', 5:'FDR 5' }

function OwnershipBar({ pct, max = 20 }) {
  const width = Math.min((pct / max) * 100, 100)
  const color = pct < 5 ? 'bg-emerald-500' : pct < 10 ? 'bg-yellow-400' : 'bg-orange-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${width}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-500 dark:text-slate-400 w-10 text-right">{pct.toFixed(1)}%</span>
    </div>
  )
}

function DifferentialCard({ p }) {
  const fdrColor = FDR_COLOR[p.fixture_difficulty] || 'bg-slate-500'
  const isCeiling = p.ceiling_flag === 'high_ceiling'
  return (
    <div className={`bg-white dark:bg-[#0f172a] border rounded-xl p-4 flex flex-col gap-3
      ${isCeiling ? 'border-amber-500/50 ring-1 ring-amber-500/30' : 'border-slate-200 dark:border-white/8'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded border font-medium ${POS_BADGE[p.position]}`}>{p.position}</span>
            {isCeiling && <span className="text-xs font-bold text-amber-400">🔥 Ceiling</span>}
            <span className="text-xs text-slate-500 dark:text-slate-400">🎯 Differential</span>
          </div>
          <p className="font-bold text-slate-900 dark:text-white truncate">{p.name}</p>
          <p className="text-slate-500 dark:text-slate-400 text-xs">{p.team}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-2xl font-bold text-cyan-400 font-mono">{p.predicted_points?.toFixed(1)}</p>
          <p className="text-slate-500 dark:text-slate-400 text-xs">pred pts</p>
        </div>
      </div>
      <div className="space-y-1.5 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-slate-500 dark:text-slate-400">Ownership</span>
          <span className="text-slate-900 dark:text-white font-mono">{p.ownership_pct?.toFixed(1)}%</span>
        </div>
        <OwnershipBar pct={p.ownership_pct} />
        <div className="flex items-center justify-between mt-1">
          <span className="text-slate-500 dark:text-slate-400">Form L3</span>
          <span className="font-mono text-slate-900 dark:text-white">{p.form_l3?.toFixed(1)} pts</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500 dark:text-slate-400">Value score</span>
          <span className="font-bold text-emerald-400 font-mono">{p.value_score?.toFixed(2)}</span>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className={`text-xs text-slate-900 dark:text-white px-2 py-0.5 rounded font-medium ${fdrColor}`}>
          {FDR_TEXT[p.fixture_difficulty] || 'FDR?'}
        </span>
        <span className="text-slate-600 dark:text-slate-500 text-xs italic truncate ml-2 text-right">{p.reason}</span>
      </div>
    </div>
  )
}

function CeilingAlert({ p }) {
  const fdrColor = FDR_COLOR[p.fixture_difficulty] || 'bg-slate-500'
  return (
    <div className="flex items-center gap-4 bg-amber-500/5 border border-amber-500/20 rounded-xl px-4 py-3">
      <span className="text-2xl">🔥</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold text-slate-900 dark:text-white">{p.name}</span>
          <span className={`text-xs px-2 py-0.5 rounded border font-medium ${POS_BADGE[p.position]}`}>{p.position}</span>
          <span className={`text-xs text-slate-900 dark:text-white px-2 py-0.5 rounded font-medium ${fdrColor}`}>{FDR_TEXT[p.fixture_difficulty]}</span>
        </div>
        <p className="text-slate-500 dark:text-slate-400 text-xs mt-0.5">{p.team} · Form L3: {p.form_l3?.toFixed(1)} pts</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-xl font-bold text-cyan-400 font-mono">{p.predicted_points?.toFixed(1)}</p>
        <p className="text-slate-500 dark:text-slate-400 text-xs">pred pts</p>
      </div>
    </div>
  )
}

function EdgePlayerRow({ p, type }) {
  const diffColor = type === 'diff'
    ? 'text-emerald-400'
    : 'text-orange-400'
  const icon = type === 'diff' ? '👍' : '⚠️'
  const fdrColor = FDR_COLOR[p.fixture_difficulty] || 'bg-slate-500'
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <span className="text-base">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-900 dark:text-white text-sm truncate">{p.name}</p>
        <p className="text-slate-500 dark:text-slate-400 text-xs">{p.team} · {p.position}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={`text-xs text-slate-900 dark:text-white px-1.5 py-0.5 rounded ${fdrColor}`}>{FDR_TEXT[p.fixture_difficulty]}</span>
        <span className="text-xs text-slate-500 dark:text-slate-400 font-mono w-10 text-right">{p.ownership_pct?.toFixed(1)}%</span>
        <span className={`text-sm font-bold font-mono w-12 text-right ${diffColor}`}>
          {p.diff > 0 ? '+' : ''}{p.diff?.toFixed(1)}
        </span>
      </div>
    </div>
  )
}

function EdgeTab() {
  const { data: diffs, isLoading: diffsLoading } = useQuery({
    queryKey: ['differentials'],
    queryFn: () => getDifferentials().then(r => r.data),
    staleTime: 1000 * 60 * 5,
  })
  const { data: compare, isLoading: compareLoading } = useQuery({
    queryKey: ['community-compare'],
    queryFn: () => getCommunityCompare().then(r => r.data),
    staleTime: 1000 * 60 * 5,
  })

  const differentials = Array.isArray(diffs) ? diffs : []
  const ceilingPicks  = differentials.filter(p => p.ceiling_flag === 'high_ceiling')

  const edgeSign  = (compare?.model_edge ?? 0) >= 0 ? '+' : ''
  const edgeColor = (compare?.model_edge ?? 0) >= 0 ? 'text-emerald-400' : 'text-orange-400'

  return (
    <div className="space-y-8">

      {/* ── Section 1: Differentials ───────────────────────────────────────── */}
      <div>
        <div className="mb-4">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            🎯 Differential Picks
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
            Players the model rates highly that &lt;15% of managers own — sorted by value score
          </p>
        </div>
        {diffsLoading && (
          <div className="text-center text-slate-500 dark:text-slate-400 animate-pulse py-12">Loading differentials…</div>
        )}
        {!diffsLoading && differentials.length === 0 && (
          <div className="bg-white dark:bg-[#0f172a] border border-dashed border-slate-200 dark:border-white/10 rounded-xl p-10 text-center text-slate-500 dark:text-slate-400">
            No differentials found for this GW.
          </div>
        )}
        {!diffsLoading && differentials.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {differentials.map(p => <DifferentialCard key={p.id} p={p} />)}
          </div>
        )}
      </div>

      {/* ── Section 2: High Ceiling Alerts ─────────────────────────────────── */}
      <div>
        <div className="mb-4">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            🔥 Ceiling Picks this GW
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
            Low-owned players with high predicted pts, easy fixture AND good recent form — all three met
          </p>
        </div>
        {diffsLoading && (
          <div className="text-center text-slate-500 dark:text-slate-400 animate-pulse py-8">Loading…</div>
        )}
        {!diffsLoading && ceilingPicks.length === 0 && (
          <div className="bg-white dark:bg-[#0f172a] border border-dashed border-slate-200 dark:border-white/10 rounded-xl p-8 text-center text-slate-500 dark:text-slate-400">
            No high-ceiling differential picks this GW — no one meets all three criteria (pts × FDR × form).
          </div>
        )}
        {!diffsLoading && ceilingPicks.length > 0 && (
          <div className="space-y-2">
            {ceilingPicks.map(p => <CeilingAlert key={p.id} p={p} />)}
          </div>
        )}
      </div>

      {/* ── Section 3: Model vs Community ──────────────────────────────────── */}
      <div>
        <div className="mb-4">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            ⚖️ Model vs Community
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
            Where the model disagrees with FPL community consensus (proxy: FPL form)
          </p>
        </div>

        {compareLoading && (
          <div className="text-center text-slate-500 dark:text-slate-400 animate-pulse py-12">Loading comparison…</div>
        )}

        {!compareLoading && compare && (
          <div className="space-y-6">
            {/* Score comparison */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-5 text-center">
                <p className="text-slate-600 dark:text-slate-500 text-xs uppercase tracking-wider mb-2">Community XI</p>
                <p className="text-3xl font-bold font-mono text-slate-900 dark:text-white">{compare.community_xi_predicted}</p>
                <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">ownership-weighted pts</p>
              </div>
              <div className={`border rounded-xl p-5 text-center ${(compare.model_edge ?? 0) >= 0 ? 'bg-emerald-900/10 border-emerald-700/40' : 'bg-orange-900/10 border-orange-700/40'}`}>
                <p className="text-slate-600 dark:text-slate-500 text-xs uppercase tracking-wider mb-2">Model Edge</p>
                <p className={`text-3xl font-bold font-mono ${edgeColor}`}>{edgeSign}{compare.model_edge}</p>
                <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">{(compare.model_edge ?? 0) >= 0 ? 'model outperforms' : 'model below community'}</p>
              </div>
              <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-5 text-center">
                <p className="text-slate-600 dark:text-slate-500 text-xs uppercase tracking-wider mb-2">Model XI</p>
                <p className="text-3xl font-bold font-mono text-cyan-400">{compare.model_xi_predicted}</p>
                <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">calibrated prediction</p>
              </div>
            </div>

            {/* Differentials & Traps */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white dark:bg-[#0f172a] border border-emerald-700/30 rounded-xl overflow-hidden">
                <div className="px-4 py-3 bg-emerald-900/20 border-b border-emerald-700/20">
                  <h4 className="font-semibold text-emerald-400 text-sm">Model Likes 👍</h4>
                  <p className="text-slate-600 dark:text-slate-500 text-xs mt-0.5">Model rates these much higher than their FPL form suggests</p>
                </div>
                <div className="px-4 py-2">
                  {compare.differentials?.length === 0
                    ? <p className="text-slate-500 dark:text-slate-400 text-sm py-4 text-center">No significant differentials this GW</p>
                    : compare.differentials?.map(p => <EdgePlayerRow key={p.fpl_id} p={p} type="diff" />)
                  }
                </div>
              </div>
              <div className="bg-white dark:bg-[#0f172a] border border-orange-700/30 rounded-xl overflow-hidden">
                <div className="px-4 py-3 bg-orange-900/20 border-b border-orange-700/20">
                  <h4 className="font-semibold text-orange-400 text-sm">Model Warns ⚠️</h4>
                  <p className="text-slate-600 dark:text-slate-500 text-xs mt-0.5">Popular picks the model is cold on — potential traps</p>
                </div>
                <div className="px-4 py-2">
                  {compare.traps?.length === 0
                    ? <p className="text-slate-500 dark:text-slate-400 text-sm py-4 text-center">No significant traps identified this GW</p>
                    : compare.traps?.map(p => <EdgePlayerRow key={p.fpl_id} p={p} type="trap" />)
                  }
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Predictions() {
  const [tab, setTab] = useState('team')
  const { data: gw } = useQuery({ queryKey:['current-gw'], queryFn:()=>getCurrentGw().then(r=>r.data) })

  const TABS = [
    { key: 'team',    label: 'Best Team' },
    { key: 'history', label: 'GW History' },
    { key: 'picks',   label: 'Best Picks' },
    { key: 'edge',    label: '🎯 Edge' },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
          <Zap className="w-8 h-8 text-cyan-400" />
          Predictions
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Adaptive ML scorer for {gw?.name || 'upcoming GW'} · learns from each GW result
        </p>
      </div>
      <div className="flex gap-1 bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-1 w-fit">
        {TABS.map(({key, label}) => (
          <button key={key} onClick={() => setTab(key)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${tab===key ? 'bg-cyan-600 text-slate-900 dark:text-white' : 'text-slate-500 dark:text-slate-400 hover:text-slate-900'}`}>
            {label}
          </button>
        ))}
      </div>
      {tab === 'team'    && <BestTeamTab />}
      {tab === 'history' && <GwHistoryTab />}
      {tab === 'picks'   && <BestPicksTab />}
      {tab === 'edge'    && <EdgeTab />}
    </div>
  )
}
