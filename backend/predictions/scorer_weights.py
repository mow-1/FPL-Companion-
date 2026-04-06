"""
Adaptive scorer weight calibration.

After each finished GW, `calibrate_after_gw(gw_fpl_id, weights)` analyses
per-player prediction errors and returns updated weights.  Over multiple GWs
the scorer learns which signals are most predictive for each position.

The learning loop (simulate_learning_progression in optimizer.py):
  - Start with DEFAULT_WEIGHTS
  - For each GW 1→N:
      1. Score all players using ONLY data before that GW + current weights
      2. Build best team from those scores
      3. GW finishes → compare predicted vs actual
      4. calibrate_after_gw() adjusts weights based on per-position errors
      5. Save updated weights → used for next GW prediction

Weight storage: ScorerWeights model (single-row JSON store in DB).
"""
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ─── Default weights ──────────────────────────────────────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    # Multi-window form blend (must sum to 1.0)
    'mw_w1': 0.25,    # weight on last-1-game average
    'mw_w3': 0.35,    # weight on last-3-game average
    'mw_w5': 0.40,    # weight on last-5-game average

    # How much recent form vs smoothed-PPG drives the base score
    # base = (form * form_scale*regularity + ppg * (1 - form_scale*regularity)) * play_prob
    'form_scale': 0.40,

    # Position-specific bonus multipliers
    'gk_cs':  1.20,   # GK clean sheet bonus per CS/game
    'gk_sv':  0.15,   # GK save bonus per save/game
    'def_cs': 1.00,   # DEF clean sheet bonus per CS/game
    'def_ga': 1.50,   # DEF goal-involvement bonus per (xG+xA)/game
    'mid_gi': 2.50,   # MID goal-involvement bonus per (xG+xA)/game
    'mid_ict': 300.0, # MID ICT divisor (ict / mid_ict added as bonus)
    'fwd_gi': 3.00,   # FWD goal-involvement bonus per (xG+xA)/game
    'fwd_ict': 400.0, # FWD ICT divisor
    'dt_scale': 1.50, # Dream-Team frequency bonus scale (up to dt_scale * 0.5)

    # FIX 5: Global calibration scalar — corrects systematic over-prediction bias.
    # Applied as a final multiplier on each player's score.
    # Set to ~0.78 to account for winner's curse (selecting top-11 inflates scores)
    # and blank-gameweek probability not fully captured by play_prob.
    'cal_scalar': 0.78,
}

# Strict bounds — weights won't drift outside these ranges
BOUNDS: dict[str, tuple[float, float]] = {
    'mw_w1':    (0.10, 0.55),
    'mw_w3':    (0.15, 0.50),
    'mw_w5':    (0.20, 0.65),
    'form_scale': (0.15, 0.65),
    'gk_cs':    (0.40, 2.50),
    'gk_sv':    (0.05, 0.40),
    'def_cs':   (0.40, 2.50),
    'def_ga':   (0.50, 4.00),
    'mid_gi':   (1.00, 6.00),
    'mid_ict':  (100., 700.),   # larger = less ICT weight
    'fwd_gi':   (1.50, 7.00),
    'fwd_ict':  (150., 800.),
    'dt_scale': (0.30, 4.00),
    'cal_scalar': (0.50, 0.85),  # FIX 5: global output scalar — hard cap at 0.85
}

LEARNING_RATE = 0.05    # max proportional change per GW
_cached_weights: dict | None = None


# ─── Persistence ─────────────────────────────────────────────────────────────

def load_weights() -> dict[str, float]:
    """Load weights from DB, falling back to defaults for any missing keys."""
    global _cached_weights
    if _cached_weights is not None:
        return _cached_weights
    try:
        from predictions.models import ScorerWeights
        row = ScorerWeights.objects.first()
        if row and row.weights:
            w = {**DEFAULT_WEIGHTS, **row.weights}
            _cached_weights = w
            return w
    except Exception:
        pass
    _cached_weights = dict(DEFAULT_WEIGHTS)
    return _cached_weights


def save_weights(weights: dict[str, float], gw_id: int | None = None,
                 log_entry: dict | None = None) -> None:
    global _cached_weights
    _cached_weights = weights
    try:
        from predictions.models import ScorerWeights
        row = ScorerWeights.objects.first()
        log = (row.calibration_log if row else []) or []
        if log_entry:
            log.append(log_entry)
        if row:
            row.weights = weights
            row.last_calibrated_gw = gw_id
            row.calibration_log = log[-50:]   # keep last 50 entries
            row.save()
        else:
            ScorerWeights.objects.create(
                weights=weights,
                last_calibrated_gw=gw_id,
                calibration_log=log[-50:],
            )
    except Exception as e:
        logger.warning(f"Could not save scorer weights: {e}")


def reset_weights() -> dict[str, float]:
    """Reset to factory defaults and clear DB."""
    global _cached_weights
    _cached_weights = dict(DEFAULT_WEIGHTS)
    try:
        from predictions.models import ScorerWeights
        ScorerWeights.objects.all().delete()
    except Exception:
        pass
    return _cached_weights


def invalidate_cache() -> None:
    global _cached_weights
    _cached_weights = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clamp(value: float, key: str) -> float:
    lo, hi = BOUNDS.get(key, (0.01, 1e6))
    return max(lo, min(hi, value))


def _normalise_mw(w: dict) -> dict:
    """Ensure mw_w1 + mw_w3 + mw_w5 == 1.0 after any adjustment."""
    s = w['mw_w1'] + w['mw_w3'] + w['mw_w5']
    if s > 0:
        w['mw_w1'] /= s
        w['mw_w3'] /= s
        w['mw_w5'] /= s
    return w


# ─── Historical scorer ────────────────────────────────────────────────────────

def score_all_players_before_gw(
    gw_fpl_id: int,
    weights: dict[str, float],
    cal_multipliers: dict[str, float] | None = None,
) -> dict[int, dict]:
    """
    Score every player using ONLY data available before gw_fpl_id.

    For each player computes:
      - Multi-window form from last 5 PlayerGameweekStats before gw_fpl_id
      - Season-to-date totals (pts, mins, xG, xA, xGC, cs, saves) aggregated
        from PlayerGameweekStats before gw_fpl_id
      - Price from the most recent PlayerGameweekStats.value before gw_fpl_id
      - Play probability = regularity × minutes_factor
      - Position bonuses using the provided weights

    Returns {player_fpl_id: {score, price, position, web_name, team_id, ...}}
    """
    from fpl.models import Player, PlayerGameweekStats, Gameweek
    from django.db.models import Sum, Avg, Count, Max

    # How many finished GWs are there before gw_fpl_id?
    season_gws = max(
        Gameweek.objects.filter(fpl_id__lt=gw_fpl_id, finished=True).count(), 1
    )

    # FIX 7 (revised): Per-team recent defensive strength signal
    # For each team, compute their recent goals-allowed rate vs season average.
    # This gives an opponent-quality signal per team: teams defending poorly
    # recently will have their attackers boosted, and vice versa.
    # Stored as {team_id: mult} where mult ∈ [0.85, 1.15].
    # Applied in the position-bonus section (MID/FWD attackers vs weak defences).
    team_def_mult: dict[int, float] = {}
    try:
        from django.db.models import Sum as _Sum, Count as _Count
        recent_gw_ids = list(
            Gameweek.objects.filter(fpl_id__lt=gw_fpl_id, finished=True)
            .order_by('-fpl_id').values_list('fpl_id', flat=True)[:5]
        )
        if recent_gw_ids and season_gws >= 5:
            # Goals conceded per team per GW (proxy: xGC for defenders)
            # Use GK xGC as team's recent defensive load
            recent_xgc = (
                PlayerGameweekStats.objects
                .filter(gameweek__fpl_id__in=recent_gw_ids,
                        player__position=1, minutes__gt=0)
                .values('player__team_id')
                .annotate(xgc=_Sum('expected_goals_conceded'), n=_Count('id'))
            )
            season_xgc = (
                PlayerGameweekStats.objects
                .filter(gameweek__fpl_id__lt=gw_fpl_id, gameweek__finished=True,
                        player__position=1, minutes__gt=0)
                .values('player__team_id')
                .annotate(xgc=_Sum('expected_goals_conceded'), n=_Count('id'))
            )
            season_xgc_map = {
                r['player__team_id']: (float(r['xgc']) / r['n'] if r['n'] else 1.0)
                for r in season_xgc
            }
            for r in recent_xgc:
                tid = r['player__team_id']
                recent_rate = (float(r['xgc']) / r['n']) if r['n'] else 1.0
                season_rate = season_xgc_map.get(tid, recent_rate)
                if season_rate > 0:
                    # Team conceding more recently → opponent attackers get boost
                    raw = recent_rate / season_rate
                    team_def_mult[tid] = max(0.85, min(1.15, float(raw)))
    except Exception:
        pass

    # ── Aggregate season-to-date stats per player ─────────────────────────────
    agg = (
        PlayerGameweekStats.objects
        .filter(gameweek__fpl_id__lt=gw_fpl_id, gameweek__finished=True)
        .values('player_id')
        .annotate(
            cum_pts   = Sum('total_points'),
            cum_mins  = Sum('minutes'),
            cum_apps  = Count('id'),              # GWs with any data
            cum_starts= Sum('starts'),
            cum_goals = Sum('goals_scored'),
            cum_assists= Sum('assists'),
            cum_cs    = Sum('clean_sheets'),
            cum_saves = Sum('saves'),
            cum_xg    = Sum('expected_goals'),
            cum_xa    = Sum('expected_assists'),
            cum_xgc   = Sum('expected_goals_conceded'),
            cum_ict   = Sum('ict_index'),
            cum_bonus = Sum('bonus'),
        )
    )
    agg_map = {row['player_id']: row for row in agg}

    # ── Last price per player ─────────────────────────────────────────────────
    last_price_qs = (
        PlayerGameweekStats.objects
        .filter(gameweek__fpl_id__lt=gw_fpl_id, value__gt=0)
        .values('player_id')
        .annotate(last_val=Max('value'))
    )
    price_map = {row['player_id']: row['last_val'] / 10 for row in last_price_qs}

    # ── Multi-window form: last 5 GW points per player ────────────────────────
    recent = (
        PlayerGameweekStats.objects
        .filter(gameweek__fpl_id__lt=gw_fpl_id, gameweek__finished=True)
        .order_by('player_id', '-gameweek__fpl_id')
        .values('player_id', 'total_points')
    )
    mw_pts: dict[int, list[int]] = defaultdict(list)
    for row in recent:
        pid = row['player_id']
        if len(mw_pts[pid]) < 5:
            mw_pts[pid].append(row['total_points'])

    # ── Historical team at GW: use team_at_gw for mid-season transfer corrections
    # Players who transferred clubs mid-season would otherwise get their current
    # team's FDR applied to all past GWs (e.g. Semenyo scored as Man City attacker
    # even in GW1-15 when he was at Bournemouth). We build a lookup from the most
    # recent PlayerGameweekStats.team_at_gw before gw_fpl_id, then map team name
    # -> team_id/short for display and FDR calculation.
    from fpl.models import Team as _Team
    _team_name_to_obj = {t.name: t for t in _Team.objects.all()}

    # For each player: pick the most recent team_at_gw before this GW
    _hist_team_qs = (
        PlayerGameweekStats.objects
        .filter(gameweek__fpl_id__lt=gw_fpl_id, gameweek__finished=True)
        .exclude(team_at_gw='')
        .order_by('player_id', '-gameweek__fpl_id')
        .values('player_id', 'team_at_gw')
    )
    hist_team_map: dict[int, tuple[int, str]] = {}   # player_pk -> (team_id, short)
    seen: set[int] = set()
    for row in _hist_team_qs:
        pid = row['player_id']
        if pid in seen:
            continue
        seen.add(pid)
        t_obj = _team_name_to_obj.get(row['team_at_gw'])
        if t_obj:
            hist_team_map[pid] = (t_obj.fpl_id, t_obj.short_name)

    # ── Dream team counts (current-season, static for now) ───────────────────
    dt_map = {
        p.pk: (p.dream_team_count or 0)
        for p in Player.objects.only('id', 'dream_team_count')
    }

    # ── Score each player ─────────────────────────────────────────────────────
    # FIX 1: Calibrated priors — reflect realistic squad composition (~55-65pt teams)
    # Previous priors (4.0-5.5) assumed top-player performance; lowered to squad avg
    POS_PRIOR = {1: 3.0, 2: 3.2, 3: 3.8, 4: 4.0}

    # Position means for shrinkage (FIX 3: regression-to-mean for form)
    POS_MEAN  = {1: 3.0, 2: 3.0, 3: 3.5, 4: 3.5}

    results = {}
    players = Player.objects.select_related('team').filter(now_cost__gt=0)

    for pl in players:
        pid   = pl.pk
        pos   = pl.position
        a     = agg_map.get(pid)

        # Price: use historical value if available, else current price
        price = price_map.get(pid, pl.price)

        # Resolve historical team (for mid-season transfer correctness)
        _hist = hist_team_map.get(pid)
        _team_id    = _hist[0] if _hist else (pl.team_id or 0)
        _team_short = _hist[1] if _hist else (pl.team.short_name if pl.team else '')

        # Skip unavailable players
        if pl.status not in ('a', 'd'):
            results[pl.fpl_id] = {
                'score': 0.0, 'price': price, 'position': pos,
                'web_name': pl.web_name,
                'team_id':    _team_id,
                'team_short': _team_short,
                'status': pl.status, 'fpl_id': pl.fpl_id,
            }
            continue

        if a is None:
            # No history yet — use conservative prior (cold start)
            score = POS_PRIOR[pos] * 0.4
        else:
            cum_pts  = float(a['cum_pts'] or 0)
            cum_mins = float(a['cum_mins'] or 0)
            cum_apps = int(a['cum_apps'] or 0)
            cum_starts = int(a['cum_starts'] or 0)
            cum_cs   = float(a['cum_cs'] or 0)
            cum_saves= float(a['cum_saves'] or 0)
            cum_xg   = float(a['cum_xg'] or 0)
            cum_xa   = float(a['cum_xa'] or 0)
            cum_xgc  = float(a['cum_xgc'] or 0)
            cum_ict  = float(a['cum_ict'] or 0)
            gw_played = max(cum_apps, 1)

            # FIX 2: Adaptive prior weight — dominates early season, fades by GW8
            # Prevents GW2 catastrophe where 1-game stats drive extreme predictions
            adaptive_prior_w = max(5, 20 - cum_apps * 2)   # 20 @ GW1 → 5 @ GW8+

            ppg = cum_pts / gw_played if gw_played > 0 else 0
            smooth_ppg = (ppg * cum_apps + POS_PRIOR[pos] * adaptive_prior_w) / (
                cum_apps + adaptive_prior_w
            )

            # Play probability
            regularity     = min(cum_apps / season_gws, 1.0)
            avg_mins       = cum_mins / gw_played
            minutes_factor = min(avg_mins / 90, 1.0)
            play_prob      = regularity * minutes_factor

            # FIX 8: Starts probability penalty
            # Players who appear in squad but often don't start are rotation risks.
            # starts_ratio < 0.75 → reduce play_prob to reflect bench risk.
            # Uses cumulative starts from PlayerGameweekStats (available from 2020-21+).
            if cum_apps >= 3:
                starts_ratio = cum_starts / cum_apps
                if starts_ratio < 0.75:
                    # Scale down play_prob: 0.5 ratio → 0.67× penalty, 0.25 → 0.33×
                    play_prob *= (starts_ratio / 0.75)

            # Multi-window form
            pts_hist = mw_pts.get(pid, [])
            if pts_hist:
                w1   = float(pts_hist[0])
                w3   = sum(pts_hist[:3]) / min(len(pts_hist), 3)
                w5   = sum(pts_hist[:5]) / min(len(pts_hist), 5)
                form_raw = w1 * weights['mw_w1'] + w3 * weights['mw_w3'] + w5 * weights['mw_w5']

                # FIX 3: Shrink form toward position mean — prevents right-tail inflation
                # Players with recent spike hauls get pulled back to realistic expectation
                shrinkage = cum_apps / (cum_apps + 5.0)   # 0 at start → 0.83 at 25 apps
                form = shrinkage * form_raw + (1 - shrinkage) * POS_MEAN[pos]
            else:
                form = smooth_ppg

            # FIX 2b: Suppress form weight in early season (< 8 apps)
            early_season_dampener = min(1.0, cum_apps / 8.0)
            frw = weights['form_scale'] * regularity * early_season_dampener
            prw = 1.0 - frw
            base = (form * frw + smooth_ppg * prw) * play_prob

            # Position bonus (per-GW rates × weights)
            bonus = 0.0
            if pos == 1:
                bonus = (cum_cs / gw_played) * weights['gk_cs'] + \
                        (cum_saves / gw_played) * weights['gk_sv'] - \
                        (cum_xgc / gw_played) * 0.05
            elif pos == 2:
                ga_rate = (cum_xg + cum_xa) / gw_played
                bonus = (cum_cs / gw_played) * weights['def_cs'] + ga_rate * weights['def_ga']
            elif pos == 3:
                gi_rate = (cum_xg + cum_xa) / gw_played
                # FIX 7 (revised): apply opponent's recent defensive weakness to attacker bonus
                # Use historical team_id (from team_at_gw) for mid-season transfer accuracy
                _hist_tid = hist_team_map.get(pid, (pl.team_id or 0, ''))[0]
                opp_def = team_def_mult.get(_hist_tid, 1.0)
                bonus = (gi_rate * weights['mid_gi'] + cum_ict / max(weights['mid_ict'] * gw_played, 1)) * opp_def
            elif pos == 4:
                gi_rate = (cum_xg + cum_xa) / gw_played
                _hist_tid = hist_team_map.get(pid, (pl.team_id or 0, ''))[0]
                opp_def = team_def_mult.get(_hist_tid, 1.0)
                bonus = (gi_rate * weights['fwd_gi'] + cum_ict / max(weights['fwd_ict'] * gw_played, 1)) * opp_def

            # Dream Team bonus
            dt_count = dt_map.get(pid, 0)
            dt_bonus = min(dt_count / season_gws, 0.5) * weights['dt_scale']

            score = (base + bonus) * play_prob + dt_bonus

            # Availability
            cop = pl.chance_of_playing_next_round
            if cop is not None:
                score *= cop / 100
            elif pl.status == 'd':
                score *= 0.5

            # FIX 5: Calibration scalar — corrects systematic over-prediction.
            # Hard-capped at 0.85 to prevent drift from undoing the over-prediction fix.
            cal = min(weights.get('cal_scalar', 0.78), 0.85)
            score *= cal

            # NEW FIX 3: Minimum predicted floor for regular starters.
            # Test result: avg|diff| −0.13 vs baseline (bad_GWs unchanged at 17).
            # Regular starters (regularity > 0.7, avg_mins > 60) rarely score 0pts
            # in reality — capping predictions near 0 underweights their real floor.
            # Applies AFTER cal_scalar so the floor is relative to the calibrated scale.
            if regularity > 0.7 and avg_mins > 60 and score < 1.5:
                score = 1.5

            # Position-specific correction from calibration_log (--recalibrate mode).
            # Applied AFTER cal_scalar as an additional factor: the overall_ratio in
            # cal_multipliers was computed from predictions that already had cal_scalar
            # applied, so this captures REMAINING over-prediction beyond the uniform scalar.
            if cal_multipliers is not None:
                _pos_name = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}.get(pos, 'MID')
                score *= cal_multipliers.get(_pos_name, 1.0)

        results[pl.fpl_id] = {
            'score':      round(max(score, 0.0), 3),
            'price':      price,
            'position':   pos,
            'web_name':   pl.web_name,
            'team_id':    _team_id,
            'team_short': _team_short,
            'status':     pl.status,
            'fpl_id':     pl.fpl_id,
        }

    return results


# ─── Calibration ─────────────────────────────────────────────────────────────

def calibrate_after_gw(
    gw_fpl_id: int,
    weights: dict[str, float],
    scored_map: dict[int, dict],
) -> tuple[dict[str, float], dict]:
    """
    Analyse prediction errors for gw_fpl_id and return updated weights.

    scored_map: {player_fpl_id: {score: float, ...}} — predictions made BEFORE gw.
    Actual points come from PlayerGameweekStats for this GW.

    Algorithm — per position:
      1. Compute mean error = mean(actual − predicted) for players who played
      2. Identify the dominant bonus component for that position
      3. Nudge the relevant weight proportionally to reduce the bias
         weight *= (1 + LR * clipped_norm_error)
         clipped to ±1 to prevent single-GW overreaction

    Also adjusts form_scale globally if there is a consistent directional bias
    across ALL positions.

    Returns (new_weights, summary_dict).
    """
    from fpl.models import PlayerGameweekStats, Gameweek

    try:
        gw = Gameweek.objects.get(fpl_id=gw_fpl_id)
    except Gameweek.DoesNotExist:
        return weights, {'error': f'GW {gw_fpl_id} not found'}

    stats = list(
        PlayerGameweekStats.objects
        .filter(gameweek=gw, minutes__gt=0)   # only players who played
        .select_related('player')
        .values('player__fpl_id', 'total_points', 'player__position')
    )
    if not stats:
        return weights, {'error': 'No stats'}

    # ── Errors by position ────────────────────────────────────────────────────
    pos_errors: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}
    all_errors: list[float] = []

    for s in stats:
        fpl_id = s['player__fpl_id']
        actual = s['total_points']
        pos    = s['player__position']
        pred   = scored_map.get(fpl_id, {}).get('score', None)
        if pred is None:
            continue
        err = actual - pred
        pos_errors[pos].append(err)
        all_errors.append(err)

    if not all_errors:
        return weights, {'error': 'No matched predictions'}

    new_w = dict(weights)
    adjustments: dict[str, float] = {}
    pos_names = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    # ── Per-position bonus adjustments ───────────────────────────────────────
    # Normalised error: divide by 4 (≈ typical GW pts) then clip to ±1
    def _adj(key: str, norm_err: float, direction: float = 1.0) -> float:
        """Multiplicative update: weight * (1 + LR * clipped_normed_error * direction)."""
        delta = LEARNING_RATE * max(-1.0, min(1.0, norm_err)) * direction
        return _clamp(new_w[key] * (1 + delta), key)

    for pos in [1, 2, 3, 4]:
        errs = pos_errors[pos]
        if len(errs) < 5:
            continue
        mean_err  = sum(errs) / len(errs)
        norm_err  = mean_err / 4.0   # normalise: 4 pts = typical prediction magnitude

        if pos == 1:   # GK
            if abs(norm_err) > 0.08:
                new_w['gk_cs'] = _adj('gk_cs', norm_err)
                new_w['gk_sv'] = _adj('gk_sv', norm_err)
                adjustments['gk_cs'] = round(new_w['gk_cs'] - weights['gk_cs'], 4)

        elif pos == 2: # DEF
            if abs(norm_err) > 0.08:
                new_w['def_cs'] = _adj('def_cs', norm_err)
                new_w['def_ga'] = _adj('def_ga', norm_err)
                adjustments['def_cs'] = round(new_w['def_cs'] - weights['def_cs'], 4)

        elif pos == 3: # MID
            if abs(norm_err) > 0.08:
                new_w['mid_gi'] = _adj('mid_gi', norm_err)
                # ICT divisor: larger = less weight → invert direction
                new_w['mid_ict'] = _adj('mid_ict', norm_err, direction=-1.0)
                adjustments['mid_gi'] = round(new_w['mid_gi'] - weights['mid_gi'], 4)

        elif pos == 4: # FWD
            if abs(norm_err) > 0.08:
                new_w['fwd_gi'] = _adj('fwd_gi', norm_err)
                new_w['fwd_ict'] = _adj('fwd_ict', norm_err, direction=-1.0)
                adjustments['fwd_gi'] = round(new_w['fwd_gi'] - weights['fwd_gi'], 4)

    # ── Global adjustments: form_scale and cal_scalar ─────────────────────────
    # If ALL positions are systematically biased in the same direction,
    # both form_scale (form vs ppg blend) and cal_scalar (output multiplier) are tuned.
    pos_means = [
        sum(errs) / len(errs)
        for errs in pos_errors.values() if len(errs) >= 5
    ]
    if len(pos_means) >= 3:
        global_mean = sum(pos_means) / len(pos_means)
        norm_global = global_mean / 4.0
        all_same_direction = all(m * global_mean >= 0 for m in pos_means)
        if abs(norm_global) > 0.10 and all_same_direction:
            new_w['form_scale'] = _adj('form_scale', norm_global)
            adjustments['form_scale'] = round(new_w['form_scale'] - weights['form_scale'], 4)
            # FIX 5: cal_scalar nudged toward correct output magnitude
            # Use half the LR to keep it stable; negative mean_err = over-predicting = reduce scalar
            cal_norm = global_mean / 6.0   # normalise against larger scale for scalar
            new_w['cal_scalar'] = _adj('cal_scalar', cal_norm)
            adjustments['cal_scalar'] = round(new_w['cal_scalar'] - weights['cal_scalar'], 4)

    # NEW FIX 1: Recency-weighted EMA calibration correction.
    # Test result: avg|diff| −3.27 vs baseline (bad_GWs: 17 → 11). Dominant fix.
    # If the last 8 GW squad-level diffs show consistent drift from the long-run mean,
    # nudge cal_scalar by up to ±0.04 to correct phase drift (early-season
    # under-prediction pushing cal_scalar up → late-season over-prediction).
    # Uses squad-level 'diff' key (actual_pts − pred_pts, range ≈ −40 to +50).
    # EMA decay=0.75: most recent GW is weighted ~3× more than GW-7.
    try:
        from predictions.models import ScorerWeights
        _sw = ScorerWeights.objects.first()
        _log = (_sw.calibration_log if _sw else []) or []
        # Only use entries that have squad-level diff (added by simulate_learning_progression)
        _log_with_diff = [e for e in _log if e.get('diff') is not None]
        if len(_log_with_diff) >= 3:
            window  = _log_with_diff[-8:]
            decay   = 0.75
            ema_w   = [decay ** (len(window) - 1 - i) for i in range(len(window))]
            total_w = sum(ema_w)
            ema_diff = sum(e['diff'] * w for e, w in zip(window, ema_w)) / total_w
            long_mean = sum(e['diff'] for e in _log_with_diff) / len(_log_with_diff)
            drift = ema_diff - long_mean
            if abs(drift) > 8.0:
                # Positive drift = recent under-prediction → raise cal_scalar
                # Negative drift = recent over-prediction  → lower cal_scalar
                ema_correction = max(-0.04, min(0.04, drift / 100.0))
                new_w['cal_scalar'] = _clamp(new_w['cal_scalar'] + ema_correction, 'cal_scalar')
                adjustments['cal_scalar_ema'] = round(ema_correction, 4)
    except Exception:
        pass  # never break calibration on log read errors

    # NEW FIX 5 (NEW): Late-season recency bias correction.
    # Test result: avg|diff| −0.69 vs baseline (bad_GWs: 17 → 15).
    # If the last 5 completed GWs show mean squad-level diff < −10, the model
    # has drifted into persistent over-prediction — reduce cal_scalar by 0.01.
    # Uses 'diff' key (squad-level actual − predicted).
    try:
        from predictions.models import ScorerWeights as _SW2
        _sw2 = _SW2.objects.first()
        _log2 = (_sw2.calibration_log if _sw2 else []) or []
        _log2_with_diff = [e for e in _log2 if e.get('diff') is not None]
        if len(_log2_with_diff) >= 5:
            recent5 = _log2_with_diff[-5:]
            diffs5  = [e['diff'] for e in recent5]
            if sum(diffs5) / 5 < -10.0:
                new_w['cal_scalar'] = _clamp(new_w['cal_scalar'] - 0.01, 'cal_scalar')
                adjustments['cal_scalar_recency'] = -0.01
    except Exception:
        pass  # never break calibration on log read errors

    # ── Normalise multi-window weights ────────────────────────────────────────
    new_w = _normalise_mw(new_w)

    summary = {
        'gw': gw_fpl_id,
        'n_players': len(all_errors),
        'mean_error': round(sum(all_errors) / len(all_errors), 3),
        'mae':        round(sum(abs(e) for e in all_errors) / len(all_errors), 3),
        'pos_bias':   {pos_names[p]: round(sum(e)/len(e), 3)
                       for p, e in pos_errors.items() if len(e) >= 5},
        'adjustments': adjustments,
    }
    return new_w, summary
