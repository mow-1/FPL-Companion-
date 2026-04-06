"""
Prediction Enhancement Test — GW1-30 backtest comparison
=========================================================
Tests 5 fixes against the recorded baseline (avg|diff|=12.30, mean_diff=+0.26).

Configurations tested
---------------------
  0  BASELINE       — no changes, replicates current production behaviour
  1  FIX1_ONLY      — recency-weighted calibration (EMA last 8 GWs)
  2  FIX2_ONLY      — consecutive blank penalty for captain
  3  FIX3_ONLY      — minimum predicted floor for regular starters
  4  FIX4_ONLY      — DEF clean-sheet correlation penalty
  5  FIX5_ONLY      — late-season recency bias correction
  6  ALL_FIXES       — all 5 applied together

For each config, runs GW1-30 from scratch (reset=True) and reports:
  avg|diff|, mean_diff, std_diff, bad_gw_count (diff<-15), haaland_cap_count

Results are written to test_fixes_results.md at the end.

Run with:  python test_fixes.py  (from backend/)
"""
import os, sys, time, statistics, math

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from collections import defaultdict
from fpl.models import Player, PlayerGameweekStats, Gameweek, Fixture, Team
from predictions.models import ScorerWeights
from predictions.scorer_weights import (
    DEFAULT_WEIGHTS, BOUNDS, LEARNING_RATE,
    _clamp, _normalise_mw,
)
from predictions.optimizer import _build_squad

# ─── shared data loaded once ─────────────────────────────────────────────────

print("Loading shared data...", flush=True)

_finished_gws = list(
    Gameweek.objects.filter(finished=True).order_by('fpl_id').values_list('fpl_id', flat=True)
)[:30]  # GW1-30

_dt_map = {p.fpl_id: (p.dream_team_count or 0) for p in Player.objects.only('fpl_id', 'dream_team_count')}
_all_players = list(Player.objects.select_related('team').filter(now_cost__gt=0))

# Pre-load all PlayerGameweekStats for GW1-30 into memory
_all_stats = list(
    PlayerGameweekStats.objects
    .filter(gameweek__fpl_id__lte=30)
    .select_related('player', 'gameweek')
    .values('player__fpl_id', 'player__position', 'player__pk', 'gameweek__fpl_id', 'gameweek__finished',
            'total_points', 'minutes', 'starts', 'goals_scored', 'assists', 'clean_sheets',
            'saves', 'expected_goals', 'expected_assists', 'expected_goals_conceded',
            'ict_index', 'bonus', 'value', 'team_at_gw')
)

# Index: {gw_id: [stat_row, ...]}
_stats_by_gw: dict[int, list] = defaultdict(list)
# Index: {player_pk: [stat_row sorted by gw desc, ...]}  for rolling lookups
_stats_by_player: dict[int, list] = defaultdict(list)
for s in _all_stats:
    _stats_by_gw[s['gameweek__fpl_id']].append(s)
    _stats_by_player[s['player__pk']].append(s)
# Sort per-player by gw desc for recent-first window
for pid in _stats_by_player:
    _stats_by_player[pid].sort(key=lambda x: x['gameweek__fpl_id'], reverse=True)

# Team name → Team object
_team_name_to_short = {t.name: t.short_name for t in Team.objects.all()}
_team_name_to_id    = {t.name: t.fpl_id     for t in Team.objects.all()}

# Fixture FDR per team per GW
_fdr_by_gw: dict[int, dict[int, int]] = defaultdict(dict)  # gw_id → {team_fpl_id: fdr}
for f in Fixture.objects.select_related('team_h', 'team_a', 'gameweek').filter(gameweek__fpl_id__lte=30):
    gw_id = f.gameweek.fpl_id
    if f.team_h and f.team_h_difficulty:
        _fdr_by_gw[gw_id][f.team_h.fpl_id] = f.team_h_difficulty
    if f.team_a and f.team_a_difficulty:
        _fdr_by_gw[gw_id][f.team_a.fpl_id] = f.team_a_difficulty

print(f"  Players: {len(_all_players)}, GW stat rows: {len(_all_stats)}", flush=True)
print("Done loading.\n", flush=True)


# ─── fast scorer (uses pre-loaded data) ──────────────────────────────────────

def fast_score_players(gw_id: int, weights: dict, fix3_floor: bool = False) -> dict[int, dict]:
    """
    Score every player using only data before gw_id.
    Uses pre-loaded data instead of DB queries for speed.
    fix3_floor: if True, apply min 1.5pt floor for regular starters (Fix 3).
    """
    # Stats before this GW
    before_rows = [s for s in _all_stats
                   if s['gameweek__fpl_id'] < gw_id and s['gameweek__finished']]

    season_gws = max(len({s['gameweek__fpl_id'] for s in before_rows}), 1)

    # Aggregate per player
    agg: dict[int, dict] = {}  # player_pk → agg
    for s in before_rows:
        pk = s['player__pk']
        if pk not in agg:
            agg[pk] = dict(cum_pts=0, cum_mins=0, cum_apps=0, cum_starts=0,
                           cum_cs=0, cum_saves=0, cum_xg=0.0, cum_xa=0.0,
                           cum_xgc=0.0, cum_ict=0.0, last_val=0, last_team='')
        a = agg[pk]
        a['cum_pts']   += s['total_points'] or 0
        a['cum_mins']  += s['minutes'] or 0
        a['cum_apps']  += 1
        a['cum_starts']+= s['starts'] or 0
        a['cum_cs']    += s['clean_sheets'] or 0
        a['cum_saves'] += s['saves'] or 0
        a['cum_xg']    += float(s['expected_goals'] or 0)
        a['cum_xa']    += float(s['expected_assists'] or 0)
        a['cum_xgc']   += float(s['expected_goals_conceded'] or 0)
        a['cum_ict']   += float(s['ict_index'] or 0)
        if s['value']:
            a['last_val'] = s['value']
        if s['team_at_gw']:
            a['last_team'] = s['team_at_gw']

    # Multi-window form (last 5)
    mw_pts: dict[int, list] = {}
    for pk, rows in _stats_by_player.items():
        before = [r for r in rows if r['gameweek__fpl_id'] < gw_id and r['gameweek__finished']]
        mw_pts[pk] = [r['total_points'] for r in before[:5]]

    # Team defensive multiplier (Fix 7 from original - keep as-is)
    team_def_mult: dict[str, float] = {}
    recent_gw_ids = sorted(
        {s['gameweek__fpl_id'] for s in before_rows}, reverse=True
    )[:5]
    if len(recent_gw_ids) >= 5:
        recent_gk = [s for s in before_rows if s['gameweek__fpl_id'] in recent_gw_ids
                     and s['player__position'] == 1 and s['minutes']]
        season_gk = [s for s in before_rows if s['player__position'] == 1 and s['minutes']]
        # team_at_gw → xgc rates
        _r_xgc: dict[str, list] = defaultdict(list)
        _s_xgc: dict[str, list] = defaultdict(list)
        for s in recent_gk:
            if s['team_at_gw']:
                _r_xgc[s['team_at_gw']].append(float(s['expected_goals_conceded'] or 0))
        for s in season_gk:
            if s['team_at_gw']:
                _s_xgc[s['team_at_gw']].append(float(s['expected_goals_conceded'] or 0))
        for team, vals in _r_xgc.items():
            r_rate = sum(vals) / len(vals)
            s_vals = _s_xgc.get(team, vals)
            s_rate = sum(s_vals) / len(s_vals) if s_vals else r_rate
            if s_rate > 0:
                team_def_mult[team] = max(0.85, min(1.15, r_rate / s_rate))

    POS_PRIOR = {1: 3.0, 2: 3.2, 3: 3.8, 4: 4.0}
    POS_MEAN  = {1: 3.0, 2: 3.0, 3: 3.5, 4: 3.5}

    results = {}
    for pl in _all_players:
        pid  = pl.pk
        pos  = pl.position
        a    = agg.get(pid)
        price = (a['last_val'] / 10) if a and a['last_val'] else pl.price
        team_short = (a['last_team'] if a and a['last_team']
                      else (pl.team.short_name if pl.team else ''))
        team_id = pl.team.fpl_id if pl.team else 0

        if pl.status not in ('a', 'd'):
            results[pl.fpl_id] = {'score': 0.0, 'price': price, 'position': pos,
                                   'web_name': pl.web_name, 'team_id': team_id,
                                   'team_short': team_short, 'status': pl.status,
                                   'fpl_id': pl.fpl_id, 'pk': pid}
            continue

        if a is None:
            score = POS_PRIOR[pos] * 0.4
        else:
            cum_pts   = float(a['cum_pts'])
            cum_mins  = float(a['cum_mins'])
            cum_apps  = int(a['cum_apps'])
            cum_starts= int(a['cum_starts'])
            cum_cs    = float(a['cum_cs'])
            cum_saves = float(a['cum_saves'])
            cum_xg    = float(a['cum_xg'])
            cum_xa    = float(a['cum_xa'])
            cum_xgc   = float(a['cum_xgc'])
            cum_ict   = float(a['cum_ict'])
            gw_played = max(cum_apps, 1)

            adaptive_prior_w = max(5, 20 - cum_apps * 2)
            ppg = cum_pts / gw_played
            smooth_ppg = (ppg * cum_apps + POS_PRIOR[pos] * adaptive_prior_w) / (
                cum_apps + adaptive_prior_w)

            regularity     = min(cum_apps / season_gws, 1.0)
            avg_mins       = cum_mins / gw_played
            minutes_factor = min(avg_mins / 90, 1.0)
            play_prob      = regularity * minutes_factor

            if cum_apps >= 3:
                starts_ratio = cum_starts / cum_apps
                if starts_ratio < 0.75:
                    play_prob *= (starts_ratio / 0.75)

            pts_hist = mw_pts.get(pid, [])
            if pts_hist:
                w1  = float(pts_hist[0])
                w3  = sum(pts_hist[:3]) / min(len(pts_hist), 3)
                w5  = sum(pts_hist[:5]) / min(len(pts_hist), 5)
                form_raw = w1 * weights['mw_w1'] + w3 * weights['mw_w3'] + w5 * weights['mw_w5']
                shrinkage = cum_apps / (cum_apps + 5.0)
                form = shrinkage * form_raw + (1 - shrinkage) * POS_MEAN[pos]
            else:
                form = smooth_ppg

            early_damp = min(1.0, cum_apps / 8.0)
            frw  = weights['form_scale'] * regularity * early_damp
            base = (form * frw + smooth_ppg * (1 - frw)) * play_prob

            bonus = 0.0
            opp_def = team_def_mult.get(team_short, 1.0)
            if pos == 1:
                bonus = (cum_cs / gw_played) * weights['gk_cs'] + \
                        (cum_saves / gw_played) * weights['gk_sv'] - \
                        (cum_xgc / gw_played) * 0.05
            elif pos == 2:
                bonus = (cum_cs / gw_played) * weights['def_cs'] + \
                        ((cum_xg + cum_xa) / gw_played) * weights['def_ga']
            elif pos == 3:
                bonus = ((cum_xg + cum_xa) / gw_played * weights['mid_gi'] +
                         cum_ict / max(weights['mid_ict'] * gw_played, 1)) * opp_def
            elif pos == 4:
                bonus = ((cum_xg + cum_xa) / gw_played * weights['fwd_gi'] +
                         cum_ict / max(weights['fwd_ict'] * gw_played, 1)) * opp_def

            dt_count = _dt_map.get(pl.fpl_id, 0)
            dt_bonus = min(dt_count / season_gws, 0.5) * weights['dt_scale']
            score = (base + bonus) * play_prob + dt_bonus

            cop = pl.chance_of_playing_next_round
            if cop is not None:
                score *= cop / 100
            elif pl.status == 'd':
                score *= 0.5

            cal = min(weights.get('cal_scalar', 0.78), 0.85)
            score *= cal

            # FIX 3: Minimum floor for regular starters
            if fix3_floor and regularity > 0.7 and (avg_mins) > 60 and score < 1.5:
                score = 1.5

        results[pl.fpl_id] = {
            'score':      round(max(score, 0.0), 3),
            'price':      price,
            'position':   pos,
            'web_name':   pl.web_name,
            'team_id':    team_id,
            'team_short': team_short,
            'status':     pl.status,
            'fpl_id':     pl.fpl_id,
            'pk':         pid,
        }
    return results


# ─── fast calibrate ───────────────────────────────────────────────────────────

def fast_calibrate(gw_id: int, weights: dict, scored_map: dict,
                   recent_log: list,
                   fix1_ema: bool = False,
                   fix5_recency: bool = False) -> tuple[dict, dict]:
    """
    Calibrate weights after a GW. Uses pre-loaded stats.
    fix1_ema: use exponential moving average from recent_log (Fix 1).
    fix5_recency: add late-season recency correction (Fix 5).
    """
    gw_stats = [s for s in _stats_by_gw[gw_id] if s['minutes'] and s['minutes'] > 0]
    if not gw_stats:
        return weights, {'error': 'No stats'}

    pos_errors: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    all_errors: list = []
    for s in gw_stats:
        fid  = s['player__fpl_id']
        pos  = s['player__position']
        pred = scored_map.get(fid, {}).get('score')
        if pred is None:
            continue
        err = s['total_points'] - pred
        pos_errors[pos].append(err)
        all_errors.append(err)

    if not all_errors:
        return weights, {'error': 'No matches'}

    new_w = dict(weights)
    adjustments = {}
    pos_names = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    def _adj(key, norm_err, direction=1.0):
        delta = LEARNING_RATE * max(-1.0, min(1.0, norm_err)) * direction
        return _clamp(new_w[key] * (1 + delta), key)

    for pos in [1, 2, 3, 4]:
        errs = pos_errors[pos]
        if len(errs) < 5:
            continue
        mean_err = sum(errs) / len(errs)
        norm_err = mean_err / 4.0
        if pos == 1 and abs(norm_err) > 0.08:
            new_w['gk_cs'] = _adj('gk_cs', norm_err)
            new_w['gk_sv'] = _adj('gk_sv', norm_err)
            adjustments['gk_cs'] = round(new_w['gk_cs'] - weights['gk_cs'], 4)
        elif pos == 2 and abs(norm_err) > 0.08:
            new_w['def_cs'] = _adj('def_cs', norm_err)
            new_w['def_ga'] = _adj('def_ga', norm_err)
            adjustments['def_cs'] = round(new_w['def_cs'] - weights['def_cs'], 4)
        elif pos == 3 and abs(norm_err) > 0.08:
            new_w['mid_gi'] = _adj('mid_gi', norm_err)
            new_w['mid_ict'] = _adj('mid_ict', norm_err, direction=-1.0)
            adjustments['mid_gi'] = round(new_w['mid_gi'] - weights['mid_gi'], 4)
        elif pos == 4 and abs(norm_err) > 0.08:
            new_w['fwd_gi'] = _adj('fwd_gi', norm_err)
            new_w['fwd_ict'] = _adj('fwd_ict', norm_err, direction=-1.0)
            adjustments['fwd_gi'] = round(new_w['fwd_gi'] - weights['fwd_gi'], 4)

    pos_means = [sum(e)/len(e) for e in pos_errors.values() if len(e) >= 5]
    if len(pos_means) >= 3:
        global_mean  = sum(pos_means) / len(pos_means)
        norm_global  = global_mean / 4.0
        all_same_dir = all(m * global_mean >= 0 for m in pos_means)
        if abs(norm_global) > 0.10 and all_same_dir:
            new_w['form_scale'] = _adj('form_scale', norm_global)
            adjustments['form_scale'] = round(new_w['form_scale'] - weights['form_scale'], 4)
            cal_norm = global_mean / 6.0
            new_w['cal_scalar'] = _adj('cal_scalar', cal_norm)
            adjustments['cal_scalar'] = round(new_w['cal_scalar'] - weights['cal_scalar'], 4)

    # FIX 1: Recency-weighted calibration correction
    # If the last 5 GWs in the growing log show consistent drift vs the
    # long-run mean, apply an additional nudge to cal_scalar to correct it.
    # Uses EMA with decay=0.75 (recent GWs weighted ~3× more than 5 GWs ago).
    if fix1_ema and len(recent_log) >= 3:
        window = recent_log[-8:]  # last 8 completed GWs
        decay  = 0.75
        weights_ema = [decay ** (len(window) - 1 - i) for i in range(len(window))]
        total_w = sum(weights_ema)
        ema_diff = sum(e['diff'] * w for e, w in zip(window, weights_ema)) / total_w
        long_mean_diff = sum(e['diff'] for e in recent_log) / len(recent_log)
        # If recent drift diverges from long-run mean by > 8pts, correct
        drift = ema_diff - long_mean_diff
        if abs(drift) > 8.0:
            # Positive drift = recent under-prediction → raise cal_scalar slightly
            # Negative drift = recent over-prediction  → lower cal_scalar slightly
            correction = max(-0.04, min(0.04, drift / 100.0))
            new_w['cal_scalar'] = _clamp(new_w['cal_scalar'] + correction, 'cal_scalar')
            adjustments['cal_scalar_ema'] = round(correction, 4)

    # FIX 5: Late-season recency bias correction
    # If the last 5 completed GWs all show over-prediction (diff < 0) and
    # the mean recent diff < -10, nudge cal_scalar down by 0.01 to correct.
    if fix5_recency and len(recent_log) >= 5:
        recent5 = recent_log[-5:]
        recent5_diff = [e['diff'] for e in recent5 if e.get('diff') is not None]
        if len(recent5_diff) == 5:
            mean_r5 = sum(recent5_diff) / 5
            if mean_r5 < -10.0:
                # All recent GWs over-predicting badly → reduce cal_scalar by 0.01
                new_w['cal_scalar'] = _clamp(new_w['cal_scalar'] - 0.01, 'cal_scalar')
                adjustments['cal_scalar_fix5'] = -0.01

    new_w = _normalise_mw(new_w)

    pos_bias = {pos_names[p]: round(sum(e)/len(e), 3)
                for p, e in pos_errors.items() if len(e) >= 5}
    summary = {
        'n_players': len(all_errors),
        'mean_error': round(sum(all_errors)/len(all_errors), 3),
        'mae': round(sum(abs(e) for e in all_errors)/len(all_errors), 3),
        'pos_bias': pos_bias,
        'adjustments': adjustments,
    }
    return new_w, summary


# ─── run one simulation config ───────────────────────────────────────────────

def run_simulation(
    label: str,
    fix1_ema: bool    = False,
    fix2_consec: bool = False,
    fix3_floor: bool  = False,
    fix4_def_corr: bool = False,
    fix5_recency: bool  = False,
) -> list[dict]:
    """
    Run GW1-30 simulation with specified fix flags.
    Returns per-GW result dicts.
    """
    FDR_MULT = {1: 1.15, 2: 1.08, 3: 1.0, 4: 0.88, 5: 0.75}
    weights  = dict(DEFAULT_WEIGHTS)
    results  = []
    recent_log = []  # growing log for fix1/fix5 context

    t0 = time.time()
    print(f"  Running [{label}]", end='', flush=True)

    for gw_id in _finished_gws:
        # 1. Score
        scored_map = fast_score_players(gw_id, weights, fix3_floor=fix3_floor)

        # 2. Build squad candidates
        candidates = [
            {
                'fpl_id':           v['fpl_id'],
                'web_name':         v['web_name'],
                'team_name':        '',
                'team_short':       v['team_short'],
                'team_id':          v['team_id'],
                'position':         v['position'],
                'position_name':    {1:'GK',2:'DEF',3:'MID',4:'FWD'}.get(v['position'],''),
                'price':            v['price'],
                'predicted_points': v['score'],
                'total_points':     0,
                'form':             0.0,
                'status':           v['status'],
                'photo_code':       None,
            }
            for v in scored_map.values()
            if v['status'] in ('a', 'd') and v['price'] > 0 and v['score'] > 0
        ]

        # FIX 4: DEF clean-sheet correlation penalty
        # Apply 0.92× to the 3rd+ DEF from the same team in the candidate pool.
        # This discourages stacking 3 DEF from one team — if their CS fails, all 3 score 1pt.
        if fix4_def_corr:
            def_cands = sorted([c for c in candidates if c['position'] == 2],
                               key=lambda x: x['predicted_points'], reverse=True)
            team_def_count: dict[int, int] = {}
            for c in def_cands:
                tid = c['team_id']
                team_def_count[tid] = team_def_count.get(tid, 0) + 1
                if team_def_count[tid] >= 3:
                    c['predicted_points'] = round(c['predicted_points'] * 0.92, 3)

        candidates.sort(key=lambda x: x['predicted_points'], reverse=True)
        xi, bench = _build_squad(candidates, 100.0)
        if not xi:
            results.append({'gw': gw_id, 'error': 'No squad'})
            weights, _ = fast_calibrate(gw_id, weights, scored_map, recent_log, fix1_ema, fix5_recency)
            continue

        # FDR map for this GW
        fdr_map = _fdr_by_gw.get(gw_id, {})

        # Blank rates
        blank_rates: dict[int, float] = {}
        consec_blanks: dict[int, int] = {}
        for p in xi:
            fid = p['fpl_id']
            pid = next((v['pk'] for v in scored_map.values() if v['fpl_id'] == fid), None)
            if pid is None:
                blank_rates[fid] = 0.25
                consec_blanks[fid] = 0
                continue
            player_rows = [r for r in _stats_by_player.get(pid, [])
                           if r['gameweek__fpl_id'] < gw_id and r['minutes'] and r['minutes'] > 0]
            total = len(player_rows)
            blanks = sum(1 for r in player_rows if r['total_points'] <= 2)
            blank_rates[fid] = blanks / total if total >= 3 else 0.25

            # FIX 2: Count consecutive blanks in last 3 GWs (most recent first)
            if fix2_consec:
                recent3 = player_rows[:3]  # already sorted desc by gw
                cb = 0
                for r in recent3:
                    if r['total_points'] <= 2:
                        cb += 1
                    else:
                        break
                consec_blanks[fid] = cb
            else:
                consec_blanks[fid] = 0

        def _cap_util(p):
            fid = p['fpl_id']
            fdr = fdr_map.get(p['team_id'], 3)
            br  = blank_rates.get(fid, 0.25)
            dt  = _dt_map.get(fid, 0)
            blank_penalty = (1.0 - br) ** 0.6
            # FIX 2: Consecutive blank penalty — if blanked 2+ of last 3, apply extra 0.70×
            if fix2_consec and consec_blanks.get(fid, 0) >= 2:
                blank_penalty *= 0.70
            adj_pts = p['predicted_points'] * FDR_MULT.get(fdr, 1.0) * blank_penalty
            return adj_pts * 2 + dt * 0.5

        xi_sorted  = sorted(xi, key=_cap_util, reverse=True)
        captain_id = xi_sorted[0]['fpl_id']

        pred_xi_pts = round(sum(
            p['predicted_points'] * (2 if p['fpl_id'] == captain_id else 1) for p in xi
        ), 1)

        # Actuals
        actuals = {s['player__fpl_id']: s['total_points'] for s in _stats_by_gw[gw_id]}
        actual_xi_pts = round(sum(
            actuals.get(p['fpl_id'], 0) * (2 if p['fpl_id'] == captain_id else 1) for p in xi
        ), 1)

        diff = round(actual_xi_pts - pred_xi_pts, 1)
        mae  = None
        errs = [abs(actuals.get(p['fpl_id'], 0) - p['predicted_points']) for p in xi if p['fpl_id'] in actuals]
        if errs:
            mae = round(sum(errs) / len(errs), 3)

        n_def = sum(1 for p in xi if p['position'] == 2)
        n_mid = sum(1 for p in xi if p['position'] == 3)
        n_fwd = sum(1 for p in xi if p['position'] == 4)

        # 3. Calibrate
        weights, cal = fast_calibrate(gw_id, weights, scored_map, recent_log, fix1_ema, fix5_recency)
        cal['predicted_pts'] = pred_xi_pts
        cal['actual_pts']    = actual_xi_pts
        cal['diff']          = diff
        recent_log.append(cal)

        result = {
            'gw':            gw_id,
            'predicted_pts': pred_xi_pts,
            'actual_pts':    actual_xi_pts,
            'diff':          diff,
            'mae':           mae,
            'captain':       xi_sorted[0]['web_name'],
            'formation':     f"{n_def}-{n_mid}-{n_fwd}",
        }
        results.append(result)
        print('.', end='', flush=True)

    elapsed = time.time() - t0
    print(f" {elapsed:.0f}s", flush=True)
    return results


# ─── metric summary ───────────────────────────────────────────────────────────

def summarise(results: list[dict], label: str) -> dict:
    valid = [r for r in results if 'diff' in r]
    diffs = [r['diff'] for r in valid]
    maes  = [r['mae']  for r in valid if r.get('mae')]
    if not diffs:
        return {}
    mean_diff  = round(sum(diffs) / len(diffs), 2)
    avg_abs    = round(sum(abs(d) for d in diffs) / len(diffs), 2)
    std_diff   = round(statistics.stdev(diffs) if len(diffs) > 1 else 0, 2)
    bad_gws    = [r for r in valid if r['diff'] < -15]
    haaland_c  = sum(1 for r in valid if 'Haaland' in r.get('captain', ''))
    avg_mae    = round(sum(maes) / len(maes), 3) if maes else 0
    return {
        'label':      label,
        'n_gws':      len(valid),
        'mean_diff':  mean_diff,
        'avg_abs':    avg_abs,
        'std_diff':   std_diff,
        'bad_gws':    len(bad_gws),
        'bad_gw_ids': [r['gw'] for r in bad_gws],
        'haaland_cap':haaland_c,
        'avg_mae':    avg_mae,
    }


# ─── run all configs ──────────────────────────────────────────────────────────

CONFIGS = [
    # label,          fix1, fix2, fix3, fix4, fix5
    ('BASELINE',      False, False, False, False, False),
    ('FIX1_EMA_CAL',  True,  False, False, False, False),
    ('FIX2_CONSEC_CAP',False,True,  False, False, False),
    ('FIX3_FLOOR',    False, False, True,  False, False),
    ('FIX4_DEF_CORR', False, False, False, True,  False),
    ('FIX5_RECENCY',  False, False, False, False, True ),
    ('ALL_FIXES',     True,  True,  True,  True,  True ),
]

print("=" * 65)
print("PREDICTION ENHANCEMENT TEST — GW1–30 BACKTEST")
print("=" * 65)
print(f"Baseline from calibration_log: avg|diff|=12.30, mean_diff=+0.26\n")

all_summaries = []
all_results   = {}

for label, f1, f2, f3, f4, f5 in CONFIGS:
    res = run_simulation(label, fix1_ema=f1, fix2_consec=f2, fix3_floor=f3,
                         fix4_def_corr=f4, fix5_recency=f5)
    s = summarise(res, label)
    all_summaries.append(s)
    all_results[label] = res


# ─── print results table ─────────────────────────────────────────────────────

print()
print("=" * 95)
print(f"{'Config':<20} {'mean_diff':>10} {'avg|diff|':>10} {'std':>7} {'bad_GWs':>8} {'H_cap':>6} {'avg_MAE':>8}")
print("-" * 95)

baseline = all_summaries[0]
for s in all_summaries:
    delta_abs = f"({s['avg_abs'] - baseline['avg_abs']:+.2f})" if s['label'] != 'BASELINE' else ""
    flag = " ✓" if s['label'] != 'BASELINE' and s['avg_abs'] < baseline['avg_abs'] else ""
    flag = " ✗" if s['label'] != 'BASELINE' and s['avg_abs'] > baseline['avg_abs'] else flag
    print(f"{s['label']:<20} {s['mean_diff']:>+10.2f} {s['avg_abs']:>10.2f} {delta_abs:>7} "
          f"{s['std_diff']:>7.2f} {s['bad_gws']:>8} {s['haaland_cap']:>6} {s['avg_mae']:>8.3f}{flag}")

print("=" * 95)
print("✓ = improvement  ✗ = regression  delta shown vs BASELINE")


# ─── per-GW detail for each config ───────────────────────────────────────────

print("\n\nPER-GW DETAILS (bad GWs highlighted)")
print("=" * 95)
for label, _, _, _, _, _ in CONFIGS:
    res = all_results[label]
    print(f"\n[{label}]")
    print(f"{'GW':>4} {'pred':>7} {'actual':>7} {'diff':>7} {'MAE':>7}  captain")
    print("-" * 55)
    for r in res:
        if 'diff' not in r:
            print(f"GW{r['gw']:>2}  ERROR")
            continue
        marker = " <-- BAD" if r['diff'] < -15 else (" <-- HAUL" if r['diff'] > 20 else "")
        print(f"GW{r['gw']:>2}  {r['predicted_pts']:>7.1f} {r['actual_pts']:>7.1f} "
              f"{r['diff']:>+7.1f} {(r['mae'] or 0):>7.3f}  {r['captain']}{marker}")


# ─── write markdown report ───────────────────────────────────────────────────

md_lines = [
    "# Prediction Enhancement Test Results",
    f"",
    f"**Baseline (recorded)**: avg|diff|=12.30, mean_diff=+0.26, bad_GWs=6",
    f"",
    f"## Summary Table",
    f"",
    f"| Config | mean_diff | avg\\|diff\\| | Δ vs baseline | std | bad_GWs | H_cap | avg_MAE | Verdict |",
    f"|--------|-----------|------------|--------------|-----|---------|-------|---------|---------|",
]
for s in all_summaries:
    delta = s['avg_abs'] - baseline['avg_abs']
    delta_str = f"{delta:+.2f}" if s['label'] != 'BASELINE' else "—"
    verdict = "—" if s['label'] == 'BASELINE' else ("✅ KEEP" if delta < 0 else "❌ REJECT")
    md_lines.append(
        f"| {s['label']} | {s['mean_diff']:+.2f} | {s['avg_abs']:.2f} | {delta_str} | "
        f"{s['std_diff']:.2f} | {s['bad_gws']} | {s['haaland_cap']} | {s['avg_mae']:.3f} | {verdict} |"
    )

md_lines += [
    "",
    "## Bad GW breakdown",
    "",
]
for s in all_summaries:
    md_lines.append(f"- **{s['label']}**: bad GWs = {s['bad_gw_ids']}")

md_lines += [
    "",
    "## Fix Descriptions",
    "",
    "| Fix | Description | Location |",
    "|-----|-------------|----------|",
    "| Fix 1 | Recency-weighted calibration (EMA last 8 GWs, decay=0.75) — corrects phase drift | `ml_loader.py: compute_calibration_multipliers()`, `scorer_weights.py: calibrate_after_gw()` |",
    "| Fix 2 | Consecutive blank captain penalty (×0.70 if blanked 2+ of last 3 GWs) | `optimizer.py: _cap_util()` in `simulate_learning_progression()` and `build_best_team()` |",
    "| Fix 3 | Predicted floor 1.5pts for regular starters (regularity>0.7, avg_mins>60) | `scorer_weights.py: score_all_players_before_gw()` |",
    "| Fix 4 | DEF clean-sheet correlation penalty (×0.92 for 3rd+ DEF from same team) | `optimizer.py: build_best_team()` and simulation loop |",
    "| Fix 5 | Late-season recency correction (nudge cal_scalar down if last 5 mean_diff < -10) | `scorer_weights.py: calibrate_after_gw()` |",
]

report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_fixes_results.md')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))

print(f"\n\nResults written to: {report_path}")
print("Done.")
