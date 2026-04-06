import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPlayers, getTeams } from '../api/fpl'
import { Search, Users, ChevronLeft, ChevronRight } from 'lucide-react'
import PlayerPhoto from '../components/PlayerPhoto'

const POSITIONS = [
  { value: '', label: 'All' },
  { value: '1', label: 'GK' },
  { value: '2', label: 'DEF' },
  { value: '3', label: 'MID' },
  { value: '4', label: 'FWD' },
]

const POS_BADGE = {
  GK:  'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  DEF: 'bg-blue-500/20   text-blue-400   border border-blue-500/30',
  MID: 'bg-cyan-500/20   text-cyan-400   border border-cyan-500/30',
  FWD: 'bg-red-500/20    text-red-400    border border-red-500/30',
}

const STATUS_DOT = {
  a: 'bg-emerald-400',
  d: 'bg-yellow-400',
  i: 'bg-red-400',
  s: 'bg-orange-400',
  u: 'bg-slate-500',
}
const STATUS_LABEL = { a: 'Available', d: 'Doubt', i: 'Injured', s: 'Suspended', u: 'Unknown' }

const SORT_OPTIONS = [
  { value: '-total_points',       label: 'Points ↓' },
  { value: 'total_points',        label: 'Points ↑' },
  { value: '-form',               label: 'Form ↓' },
  { value: '-ict_index',          label: 'ICT ↓' },
  { value: 'now_cost',            label: 'Price ↑' },
  { value: '-now_cost',           label: 'Price ↓' },
  { value: '-selected_by_percent',label: 'Ownership ↓' },
]

const inputCls = 'bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2.5 text-sm text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500 transition-colors placeholder-slate-400 dark:placeholder-slate-500'
const selectCls = inputCls + ' cursor-pointer'

export default function Players() {
  const [filters, setFilters] = useState({
    position: '', team: '', search: '', ordering: '-total_points', min_price: '', max_price: ''
  })
  const [page, setPage] = useState(1)

  const params = {
    page,
    page_size: 20,
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '')),
  }

  const { data, isLoading } = useQuery({
    queryKey: ['players', params],
    queryFn: () => getPlayers(params).then(r => r.data),
    keepPreviousData: true,
  })

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: () => getTeams().then(r => r.data.results || r.data),
  })

  const set = k => e => { setFilters(f => ({ ...f, [k]: e.target.value })); setPage(1) }
  const players = data?.results || []

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <header>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
          <Users className="w-7 h-7 text-cyan-400" />
          Players
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">Browse and filter all Premier League players.</p>
      </header>

      {/* Filters */}
      <div className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl p-4 space-y-3">
        {/* Search — full width */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600 dark:text-slate-500" />
          <input
            className={inputCls + ' w-full pl-9'}
            placeholder="Search player…"
            value={filters.search}
            onChange={set('search')}
          />
        </div>
        {/* Filter row */}
        <div className="flex flex-wrap gap-2">
          <select className={selectCls + ' flex-1 min-w-[100px]'} value={filters.position} onChange={set('position')}>
            {POSITIONS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
          <select className={selectCls + ' flex-1 min-w-[140px]'} value={filters.team} onChange={set('team')}>
            <option value="">All Teams</option>
            {(teams || []).map(t => <option key={t.fpl_id} value={t.fpl_id}>{t.name}</option>)}
          </select>
          <select className={selectCls + ' flex-1 min-w-[120px]'} value={filters.ordering} onChange={set('ordering')}>
            {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <input className={inputCls + ' w-24'} type="number" placeholder="Min £" step="0.1" value={filters.min_price} onChange={set('min_price')} />
          <input className={inputCls + ' w-24'} type="number" placeholder="Max £" step="0.1" value={filters.max_price} onChange={set('max_price')} />
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-16 bg-slate-100 dark:bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          {/* ── Mobile card view ── */}
          <div className="md:hidden space-y-2">
            {players.map(p => (
              <div key={p.fpl_id} className="bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-xl p-3 flex items-center gap-3 active:bg-slate-100 dark:bg-white/5 transition-colors">
                <PlayerPhoto code={p.code} name={p.web_name} pos={p.position_name} size="md" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="font-semibold text-slate-900 dark:text-white text-sm truncate">{p.web_name}</p>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border flex-shrink-0 ${POS_BADGE[p.position_name] || ''}`}>
                      {p.position_name}
                    </span>
                  </div>
                  <p className="text-slate-500 dark:text-slate-400 text-xs truncate">{p.team_name}</p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-yellow-400 font-mono text-xs font-medium">£{p.price?.toFixed(1)}m</span>
                    <span className="text-cyan-400 font-mono text-xs font-semibold">{p.total_points}pts</span>
                    <span className="text-slate-500 dark:text-slate-400 text-xs">Form <span className="text-slate-900 dark:text-white">{p.form}</span></span>
                    <span className="text-slate-600 dark:text-slate-500 text-xs">{p.selected_by_percent}%</span>
                  </div>
                </div>
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${STATUS_DOT[p.status] || 'bg-slate-500'}`}
                    title={STATUS_LABEL[p.status] || p.status}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* ── Desktop table ── */}
          <div className="hidden md:block bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-white/8 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider">
                    <th className="px-4 py-3.5 text-left font-semibold">Player</th>
                    <th className="px-3 py-3.5 text-left font-semibold">Pos</th>
                    <th className="px-3 py-3.5 text-left font-semibold">Team</th>
                    <th className="px-3 py-3.5 text-right font-semibold">Price</th>
                    <th className="px-3 py-3.5 text-right font-semibold">Pts</th>
                    <th className="px-3 py-3.5 text-right font-semibold">Form</th>
                    <th className="px-3 py-3.5 text-right font-semibold">ICT</th>
                    <th className="px-3 py-3.5 text-right font-semibold">xG</th>
                    <th className="px-3 py-3.5 text-right font-semibold">xA</th>
                    <th className="px-3 py-3.5 text-right font-semibold">Sel%</th>
                    <th className="px-3 py-3.5 text-center font-semibold">Fit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {players.map(p => (
                    <tr key={p.fpl_id} className="hover:bg-white/[0.03] transition-colors group">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2.5">
                          <PlayerPhoto code={p.code} name={p.web_name} pos={p.position_name} size="sm" />
                          <span className="font-medium text-slate-900 dark:text-white group-hover:text-cyan-300 transition-colors">{p.web_name}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className={`text-[10px] px-2 py-0.5 rounded font-bold border ${POS_BADGE[p.position_name] || ''}`}>
                          {p.position_name}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400 text-xs">{p.team_name}</td>
                      <td className="px-3 py-2.5 text-right text-yellow-400 font-mono text-xs font-medium">£{p.price?.toFixed(1)}m</td>
                      <td className="px-3 py-2.5 text-right text-cyan-400 font-mono font-bold">{p.total_points}</td>
                      <td className="px-3 py-2.5 text-right text-slate-300 font-mono text-xs">{p.form}</td>
                      <td className="px-3 py-2.5 text-right text-blue-400 font-mono text-xs">{p.ict_index}</td>
                      <td className="px-3 py-2.5 text-right text-purple-400 font-mono text-xs">{p.expected_goals ?? '—'}</td>
                      <td className="px-3 py-2.5 text-right text-purple-400 font-mono text-xs">{p.expected_assists ?? '—'}</td>
                      <td className="px-3 py-2.5 text-right text-slate-500 dark:text-slate-400 font-mono text-xs">{p.selected_by_percent}%</td>
                      <td className="px-3 py-2.5">
                        <div className="flex justify-center">
                          <span
                            className={`w-2.5 h-2.5 rounded-full ${STATUS_DOT[p.status] || 'bg-slate-500'}`}
                            title={STATUS_LABEL[p.status] || p.status}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <span className="text-slate-600 dark:text-slate-500 text-xs font-mono">{data?.count ?? 0} players · page {page}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-1.5 px-4 py-2 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm text-slate-300 disabled:opacity-30 hover:bg-slate-200 dark:bg-white/10 hover:text-slate-900 dark:hover:text-white transition-colors"
              >
                <ChevronLeft className="w-4 h-4" /> Prev
              </button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={!data?.next}
                className="flex items-center gap-1.5 px-4 py-2 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm text-slate-300 disabled:opacity-30 hover:bg-slate-200 dark:bg-white/10 hover:text-slate-900 dark:hover:text-white transition-colors"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
