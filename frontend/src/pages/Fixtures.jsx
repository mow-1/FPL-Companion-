import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFixtures, getGameweeks } from '../api/fpl'
import { CalendarDays, Clock } from 'lucide-react'

const FDR_STYLE = {
  1: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  2: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  3: 'bg-amber-500/20   text-amber-400   border-amber-500/30',
  4: 'bg-red-500/20     text-red-400     border-red-500/30',
  5: 'bg-red-600/25     text-red-300     border-red-600/40',
}

function FdrBadge({ difficulty }) {
  if (!difficulty) return <span className="text-slate-700 dark:text-slate-600 text-xs">—</span>
  return (
    <span className={`inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-full border ${FDR_STYLE[difficulty] || FDR_STYLE[3]}`}>
      FDR {difficulty}
    </span>
  )
}

function formatKickoff(kt) {
  if (!kt) return 'TBC'
  const d = new Date(kt)
  const day  = d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
  const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  return { day, time }
}

export default function Fixtures() {
  const [selectedGw, setSelectedGw] = useState('')

  const { data: gameweeks } = useQuery({
    queryKey: ['gameweeks'],
    queryFn: () => getGameweeks().then(r => r.data.results || r.data),
  })

  const currentGw = gameweeks?.find(g => g.is_current)?.fpl_id
  const gwId = selectedGw || currentGw

  const { data, isLoading } = useQuery({
    queryKey: ['fixtures', gwId],
    queryFn: () => getFixtures({ gameweek: gwId }).then(r => r.data.results || r.data),
    enabled: !!gwId,
  })

  const fixtures = data || []

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <header className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
            <CalendarDays className="w-7 h-7 text-cyan-400" />
            Fixtures
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">Gameweek schedule and difficulty ratings.</p>
        </div>
        <select
          value={selectedGw}
          onChange={e => setSelectedGw(e.target.value)}
          className="bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500 transition-colors cursor-pointer"
        >
          <option value="">Current GW</option>
          {gameweeks?.map(gw => (
            <option key={gw.fpl_id} value={gw.fpl_id}>{gw.name}</option>
          ))}
        </select>
      </header>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 bg-slate-100 dark:bg-white/5 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : fixtures.length === 0 ? (
        <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-12 text-center">
          <CalendarDays className="w-10 h-10 text-slate-700 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 dark:text-slate-400">No fixtures found for this gameweek.</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {fixtures.map(f => {
            const done = f.finished || f.finished_provisional
            const ko   = f.kickoff_time ? formatKickoff(f.kickoff_time) : null
            return (
              <div
                key={f.fpl_id}
                className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl px-4 py-4 hover:border-slate-300 dark:hover:border-slate-300 dark:border-white/15 hover:bg-slate-50 dark:bg-white/[0.02] transition-all"
              >
                <div className="flex items-center gap-3">
                  {/* Home team */}
                  <div className="flex-1 text-right space-y-1 min-w-0">
                    <p className="font-bold text-slate-900 dark:text-white text-base md:text-lg truncate">{f.team_h_name}</p>
                    <div className="flex items-center justify-end gap-1.5">
                      <span className="text-slate-600 dark:text-slate-500 text-xs font-mono">{f.team_h_short}</span>
                      <FdrBadge difficulty={f.team_h_difficulty} />
                    </div>
                  </div>

                  {/* Centre — score or time */}
                  <div className="flex-shrink-0 w-24 md:w-32 text-center">
                    {done ? (
                      <div className="bg-slate-100 dark:bg-white/5 rounded-xl px-3 py-2">
                        <p className="text-xl md:text-2xl font-bold font-mono text-slate-900 dark:text-white leading-none">
                          {f.team_h_score}
                          <span className="text-slate-700 dark:text-slate-600 mx-1.5">–</span>
                          {f.team_a_score}
                        </p>
                        <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">Full Time</span>
                      </div>
                    ) : (
                      <div className="bg-slate-100 dark:bg-white/5 rounded-xl px-2 py-2.5 space-y-0.5">
                        {ko ? (
                          <>
                            <p className="text-slate-900 dark:text-white font-bold text-sm leading-none">{ko.time}</p>
                            <p className="text-slate-600 dark:text-slate-500 text-[11px] leading-none">{ko.day}</p>
                          </>
                        ) : (
                          <div className="flex items-center justify-center gap-1 text-slate-600 dark:text-slate-500 text-xs">
                            <Clock className="w-3 h-3" />
                            <span>TBC</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Away team */}
                  <div className="flex-1 text-left space-y-1 min-w-0">
                    <p className="font-bold text-slate-900 dark:text-white text-base md:text-lg truncate">{f.team_a_name}</p>
                    <div className="flex items-center gap-1.5">
                      <FdrBadge difficulty={f.team_a_difficulty} />
                      <span className="text-slate-600 dark:text-slate-500 text-xs font-mono">{f.team_a_short}</span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
