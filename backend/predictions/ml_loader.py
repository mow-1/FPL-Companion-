"""
ML model loader and inference engine.
Loads trained LSTM/GRU/Ensemble models from RNN_Ready/ml_artifacts/.
Falls back to a stat-based scorer when model files are not present.
"""
import logging
import numpy as np
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

POSITION_MAP = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

BEST_MODEL_PER_POSITION = {
    'GK':  'lstm_enhanced',   # W2=92.4%, MAE=0.631
    'DEF': 'tft_enhanced',    # W2=89.5%, MAE=0.880
    'MID': 'ensemble_base',   # W2=90.9%, MAE=0.907 (LSTM component of best Ensemble)
    'FWD': 'gru_base',        # W2=88.4%, MAE=0.951
}

# Artifact directory names (relative to ML_ARTIFACTS_PATH setting).
# For documentation and debugging — get_model() derives these automatically from
# BEST_MODEL_PER_POSITION as f"{position}_{model_type}".
ARTIFACT_PATHS = {
    'GK':  'ml_artifacts/GK_lstm_enhanced',
    'DEF': 'ml_artifacts/DEF_tft_enhanced',
    'MID': 'ml_artifacts/MID_ensemble_base',
    'FWD': 'ml_artifacts/FWD_gru_base',
}

# Per-position, per-tier feature lists.
# Must match INFERENCE_FEATURES in save_artifacts.py exactly.
# Only raw features available in both the RNN_Ready CSVs and PlayerGameweekStats.
_COMMON = [
    'minutes', 'was_home', 'value', 'selected', 'transfers_balance',
    'yellow_cards', 'red_cards', 'ict_index', 'creativity', 'influence', 'threat',
]
_EXPECTED = [
    'expected_goals', 'expected_assists',
    'expected_goal_involvements', 'expected_goals_conceded',
]

FEATURES_BY_POS_TIER = {
    'GK': {
        'base':     _COMMON + ['saves', 'goals_conceded', 'clean_sheets', 'penalties_saved'],
        'enhanced': _COMMON + ['saves', 'goals_conceded', 'clean_sheets', 'penalties_saved'] + _EXPECTED,
    },
    'DEF': {
        'base':     _COMMON + ['goals_scored', 'assists', 'goals_conceded', 'clean_sheets'],
        'enhanced': _COMMON + ['goals_scored', 'assists', 'goals_conceded', 'clean_sheets'] + _EXPECTED,
    },
    'MID': {
        'base':     _COMMON + ['goals_scored', 'assists', 'clean_sheets'],
        'enhanced': _COMMON + ['goals_scored', 'assists', 'clean_sheets'] + _EXPECTED,
    },
    'FWD': {
        'base':     _COMMON + ['goals_scored', 'assists'],
        'enhanced': _COMMON + ['goals_scored', 'assists'] + _EXPECTED,
    },
}


def _get_features(position: str, model_type: str) -> list[str]:
    """Return the feature list for this position + model type."""
    tier = 'enhanced' if 'enhanced' in model_type else 'base'
    return FEATURES_BY_POS_TIER.get(position, FEATURES_BY_POS_TIER['MID'])[tier]


SEQUENCE_LENGTH = 5
_model_cache: dict = {}
_cached_season_gws: int | None = None
_cached_fixture_mults: dict | None = None
_prev_season_cache: dict | None = None   # {fpl_id: [row_dict, ...]} — raw field dicts
_calibration_cache: dict | None = None   # {pos_name: multiplier} — lazy, computed once


def compute_calibration_multipliers() -> dict[str, float]:
    """
    Compute position-specific calibration multipliers from GW history data.

    Strategy:
      - Overall ratio  = avg(actual_pts) / avg(predicted_pts) from calibration_log
        (e.g. 0.781 means model over-predicts by ~22% on average)
      - Position bias  = avg pos_bias (MAE) per position from calibration_log
        Positions with higher MAE receive slightly more aggressive deflation,
        positions with lower MAE receive slightly less.
      - Formula: multiplier[pos] = overall_ratio * (1 - normalised_excess_bias * 0.08)
        where normalised_excess_bias = (pos_mae - mean_mae) / mean_mae

    Returns e.g. {'GK': 0.82, 'DEF': 0.79, 'MID': 0.76, 'FWD': 0.78}
    Falls back to 1.0 if no calibration_log data is available.
    """
    global _calibration_cache
    if _calibration_cache is not None:
        return _calibration_cache

    result = {'GK': 1.0, 'DEF': 1.0, 'MID': 1.0, 'FWD': 1.0}
    try:
        from predictions.models import ScorerWeights

        sw = ScorerWeights.objects.first()
        if not sw or not sw.calibration_log:
            logger.info("No calibration_log found — using neutral multipliers")
            _calibration_cache = result
            return result

        log = [
            e for e in sw.calibration_log
            if e.get('actual_pts') is not None and e.get('predicted_pts') is not None
            and e['predicted_pts'] > 0
        ]
        if len(log) < 3:
            logger.info("Insufficient calibration_log entries (%d) — using neutral multipliers", len(log))
            _calibration_cache = result
            return result

        # Use raw_predicted_pts when available (written by simulate_learning_progression)
        # to avoid double-calibration: if predicted_pts is already calibrated then
        # actual/predicted ≈ 1.0 and multipliers would be near-1.0 on re-runs.
        # raw_predicted_pts is the XI score BEFORE position-specific multipliers were applied,
        # so actual/raw always reflects the true uncalibrated over-prediction ratio.
        sum_pred   = sum(e.get('raw_predicted_pts') or e['predicted_pts'] for e in log)
        sum_actual = sum(e['actual_pts'] for e in log)
        overall_ratio = sum_actual / sum_pred  # e.g. 0.781

        # Average pos_bias (MAE) per position across GWs
        from collections import defaultdict
        pos_bias_sums = defaultdict(list)
        for e in log:
            for pos, bias in e.get('pos_bias', {}).items():
                if isinstance(bias, (int, float)):
                    pos_bias_sums[pos].append(float(bias))

        pos_mae = {
            pos: sum(vals) / len(vals)
            for pos, vals in pos_bias_sums.items()
            if vals
        }

        if pos_mae:
            mean_mae = sum(pos_mae.values()) / len(pos_mae)
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                mae = pos_mae.get(pos, mean_mae)
                # Positions with above-average MAE get more deflation (smaller multiplier)
                normalised_excess = (mae - mean_mae) / max(mean_mae, 0.01)
                multiplier = overall_ratio * (1.0 - normalised_excess * 0.08)
                result[pos] = round(max(0.5, min(1.2, multiplier)), 4)
        else:
            # No pos_bias data — apply overall ratio uniformly
            for pos in result:
                result[pos] = round(overall_ratio, 4)

        logger.info(
            "Calibration multipliers (overall_ratio=%.3f, n_gws=%d): %s",
            overall_ratio, len(log), result,
        )

    except Exception as e:
        logger.warning("Could not compute calibration multipliers: %s", e)

    _calibration_cache = result
    return result

# Vaastav 2024-25 CSV — two levels above the Django project root
_PREV_SEASON_CSV = Path(settings.BASE_DIR).parent.parent / 'RNN_Ready' / 'raw' / '2024-25.csv'

# Stats that should be summed across DGW fixtures; all others take the last value
_DGW_SUM_COLS = {
    'minutes', 'goals_scored', 'assists', 'clean_sheets', 'goals_conceded',
    'own_goals', 'penalties_saved', 'penalties_missed', 'yellow_cards',
    'red_cards', 'saves', 'bonus', 'bps', 'total_points',
    'expected_goals', 'expected_assists',
    'expected_goal_involvements', 'expected_goals_conceded',
}


def _load_prev_season_tail() -> dict[int, list[dict]]:
    """
    Lazy-load the last 5 GWs of 2024-25 season from the vaastav CSV.

    DGW rows (same player, same round) are aggregated: counting stats summed,
    rate/value stats take the last value — matching how the training pipeline
    treated double gameweeks.

    Returns {fpl_id: [row_dict_earliest, ..., row_dict_latest]}
    where each row_dict contains all available raw fields as floats.
    The caller selects only the features it needs for its position/model_type.

    Cached for the process lifetime so the CSV is only parsed once.
    """
    global _prev_season_cache
    if _prev_season_cache is not None:
        return _prev_season_cache

    if not _PREV_SEASON_CSV.exists():
        logger.warning(f"Previous season CSV not found at {_PREV_SEASON_CSV}")
        _prev_season_cache = {}
        return {}

    try:
        import pandas as pd

        df = pd.read_csv(str(_PREV_SEASON_CSV), encoding='latin-1')

        # All raw stat columns we might need across any position/tier
        all_stat_cols = {
            'minutes', 'was_home', 'value', 'selected', 'transfers_balance',
            'yellow_cards', 'red_cards', 'ict_index', 'creativity', 'influence', 'threat',
            'saves', 'goals_conceded', 'clean_sheets', 'penalties_saved',
            'goals_scored', 'assists', 'own_goals', 'penalties_missed',
            'bonus', 'bps', 'total_points',
            'expected_goals', 'expected_assists',
            'expected_goal_involvements', 'expected_goals_conceded',
        }

        # Aggregate DGW rows per (element, GW)
        present_cols = [c for c in df.columns if c in all_stat_cols]
        agg_spec = {c: ('sum' if c in _DGW_SUM_COLS else 'last')
                    for c in present_cols}
        df_agg = (df.groupby(['element', 'GW'], as_index=False)
                    .agg(agg_spec)
                    .sort_values(['element', 'GW']))

        cache: dict[int, list[dict]] = {}
        for fpl_id, grp in df_agg.groupby('element'):
            tail = grp.tail(5)  # last 5 GWs (earliest → latest after sort)
            rows = [
                {col: float(row.get(col, 0) or 0) for col in present_cols}
                for _, row in tail.iterrows()
            ]
            cache[int(fpl_id)] = rows

        _prev_season_cache = cache
        logger.info("Loaded previous-season tail for %d players from vaastav 2024-25", len(cache))
        return cache

    except Exception as e:
        logger.warning(f"Could not load previous season data: {e}")
        _prev_season_cache = {}
        return {}


def _get_season_gws() -> int:
    """Return number of finished GWs this season (cached for the process lifetime)."""
    global _cached_season_gws
    if _cached_season_gws is None:
        try:
            from fpl.models import Gameweek
            _cached_season_gws = max(Gameweek.objects.filter(finished=True).count(), 1)
        except Exception:
            _cached_season_gws = 28
    return _cached_season_gws


def _get_fixture_multipliers() -> dict[int, tuple[float, float]]:
    """
    For each team in the next GW, compute fixture difficulty multipliers:
      att_mult: for MID/FWD — how easy is it to score vs this opponent's defence?
      def_mult: for GK/DEF  — how easy is it to keep CS vs this opponent's attack?

    Uses FPL team strength ratings (home/away adjusted).
    A league-average fixture → multiplier = 1.0
    Easy fixture (weak opponent) → multiplier > 1.0 (up to ~1.25)
    Hard fixture (strong opponent) → multiplier < 1.0 (down to ~0.75)

    Cached per process run so it's only computed once per prediction batch.
    """
    global _cached_fixture_mults
    if _cached_fixture_mults is not None:
        return _cached_fixture_mults

    try:
        from fpl.models import Gameweek, Fixture
        gw = (Gameweek.objects.filter(is_next=True).first()
              or Gameweek.objects.filter(is_current=True).first())
        if not gw:
            _cached_fixture_mults = {}
            return {}

        fixtures = Fixture.objects.filter(gameweek=gw).select_related('team_h', 'team_a')

        # Compute league-average strengths from all teams in fixtures
        all_def_strengths, all_att_strengths = [], []
        for f in fixtures:
            if f.team_h and f.team_a:
                all_def_strengths += [f.team_h.strength_defence_home, f.team_a.strength_defence_away]
                all_att_strengths += [f.team_h.strength_attack_home, f.team_a.strength_attack_away]

        avg_def = sum(all_def_strengths) / max(len(all_def_strengths), 1)
        avg_att = sum(all_att_strengths) / max(len(all_att_strengths), 1)
        MAX_SWING = 0.25   # max ±25% adjustment from fixture difficulty

        mults: dict[int, tuple[float, float]] = {}
        for f in fixtures:
            if not (f.team_h and f.team_a and f.team_h_id and f.team_a_id):
                continue

            # Home team faces away team's away-defence and away-attack
            opp_def_h  = f.team_a.strength_defence_away
            opp_att_h  = f.team_a.strength_attack_away
            # Away team faces home team's home-defence and home-attack
            opp_def_a  = f.team_h.strength_defence_home
            opp_att_a  = f.team_h.strength_attack_home

            def _mult(opp_str, avg, invert=False):
                raw = (avg - opp_str) / max(avg, 1)   # positive = easy, negative = hard
                if invert:
                    raw = -raw
                return round(1.0 + max(-MAX_SWING, min(MAX_SWING, raw * MAX_SWING * 4)), 3)

            # att_mult: easier to score vs weak defence → opp_def lower = easier
            # def_mult: easier to keep CS vs weak attack → opp_att lower = easier
            mults[f.team_h_id] = (_mult(opp_def_h, avg_def), _mult(opp_att_h, avg_att))
            mults[f.team_a_id] = (_mult(opp_def_a, avg_def), _mult(opp_att_a, avg_att))

        _cached_fixture_mults = mults
        return mults
    except Exception as e:
        logger.warning(f"Could not compute fixture multipliers: {e}")
        _cached_fixture_mults = {}
        return {}


def _artifacts_path() -> Path:
    return Path(getattr(settings, 'ML_ARTIFACTS_PATH', ''))


def _models_available() -> bool:
    artifacts = _artifacts_path()
    return any(
        (artifacts / f"{pos}_{m}" / 'model.keras').exists()
        for pos, m in BEST_MODEL_PER_POSITION.items()
    )


# ─── Multi-window recency ─────────────────────────────────────────────────────

def _multi_window_form(player) -> float:
    """
    Weighted blend of 1-game, 3-game, and 5-game actual point averages.

    Inspired by OpenFPL (arxiv 2508.09992): aggregating across multiple time
    horizons simultaneously outperforms any single window because:
      - 1-game window  captures short-term momentum / explosive form spikes
      - 3-game window  filters out single-game noise, confirms short-term trend
      - 5-game window  provides medium-term stability, matches FPL's own 'form'

    Weights lean toward recency (1-game heaviest) so a genuine in-form player
    rises quickly, while a cold-streak player falls quickly.

    Falls back to FPL's 'form' field when no GW stats exist in the DB.
    """
    try:
        from fpl.models import PlayerGameweekStats
        pts = list(
            PlayerGameweekStats.objects
            .filter(player=player)
            .order_by('-gameweek__fpl_id')
            .values_list('total_points', flat=True)[:5]
        )
    except Exception:
        return float(player.form or 0)

    if not pts:
        return float(player.form or 0)

    from predictions.scorer_weights import load_weights as _lw
    w = _lw()
    w1 = float(pts[0])
    w3 = sum(pts[:3]) / min(len(pts), 3)
    w5 = sum(pts[:5]) / min(len(pts), 5)
    return round(w1 * w['mw_w1'] + w3 * w['mw_w3'] + w5 * w['mw_w5'], 2)


# ─── Stat-based fallback scorer ───────────────────────────────────────────────

def _fallback_score(player) -> float:
    """
    Per-GW expected-points scorer.

    Core model:
      expected_pts = ppg_when_playing * play_probability + position_bonuses

    ppg_when_playing = FPL's points_per_game (pts per appearance).
      → Unbiased for regular starters; smoothed toward a prior for few-game players.
    play_probability = regularity (appearances / season_gws) * minutes_factor
      → Accounts for both "does the player start?" and "do they play 90 mins?"

    We also blend recent form to capture in-season hot/cold streaks, weighted
    more for regular starters (where form is meaningful) and less for rotations
    (where form from a handful of games is noise).

    This produces scores calibrated to what a player actually delivers per week
    of the season — not suppressed by blanks, but also not inflated by small samples.
    """
    pos       = player.position
    form      = _multi_window_form(player)   # 1/3/5-game weighted blend
    ppg       = float(player.points_per_game or 0)
    total_pts = player.total_points or 0
    mins      = player.minutes or 0
    ict       = float(player.ict_index or 0)
    xg        = float(player.expected_goals or 0)
    xa        = float(player.expected_assists or 0)
    xgc       = float(player.expected_goals_conceded or 0)
    cs        = player.clean_sheets or 0
    saves     = player.saves or 0

    season_gws = _get_season_gws()

    # Appearances: derived from ppg when reliable, otherwise from minutes
    appearances = (total_pts / ppg) if ppg > 0.5 else max(mins / 90, 0.5)
    gw_played   = max(appearances, 1)

    # Bayesian-smoothed ppg: blend observed ppg with a position prior.
    # For few-game players the prior dominates; for regulars, observed ppg wins.
    # Prior = league-average pts per game per position (rough FPL benchmarks).
    # Calibrated priors — squad-level averages, not top-player benchmarks
    POS_PRIOR = {1: 3.0, 2: 3.2, 3: 3.8, 4: 4.0}
    # Adaptive prior weight: dominates early season, fades by GW8
    adaptive_prior_w = max(5, 20 - int(appearances) * 2)
    smooth_ppg = (ppg * appearances + POS_PRIOR[pos] * adaptive_prior_w) / (appearances + adaptive_prior_w)

    # Play probability: fraction of season GWs the player contributes to
    regularity     = min(appearances / season_gws, 1.0)
    avg_mins       = mins / gw_played
    minutes_factor = min(avg_mins / 90, 1.0)
    play_prob      = regularity * minutes_factor

    # Load adaptive weights (calibrated after each finished GW)
    from predictions.scorer_weights import load_weights as _lw
    w = _lw()

    # FIX 3: Shrink form toward position mean — prevents right-tail inflation
    POS_MEAN = {1: 3.0, 2: 3.0, 3: 3.5, 4: 3.5}
    shrinkage = min(appearances / (appearances + 5.0), 1.0)
    form = shrinkage * form + (1 - shrinkage) * POS_MEAN.get(pos, 3.0)

    # FIX 2b: Suppress form weight in early season (< 8 apps)
    early_season_dampener = min(1.0, appearances / 8.0)

    # Base expected output = ppg-when-playing * probability-of-playing
    # Then blend with recent form (more weight for regular starters)
    form_weight = w['form_scale'] * regularity * early_season_dampener
    ppg_weight  = 1.0 - form_weight

    base_score = (form * form_weight + smooth_ppg * ppg_weight) * play_prob

    # Position-specific bonus rates (calibrated multipliers from w)
    bonus = 0.0
    if pos == 1:   # GK
        cs_rate = cs / gw_played
        sv_rate = saves / gw_played
        gc_rate = xgc / gw_played if xgc else 0
        bonus = cs_rate * w['gk_cs'] + sv_rate * w['gk_sv'] - gc_rate * 0.05
    elif pos == 2: # DEF
        cs_rate = cs / gw_played
        ga_rate = (xg + xa) / gw_played if (xg + xa) else 0
        bonus = cs_rate * w['def_cs'] + ga_rate * w['def_ga']
    elif pos == 3: # MID
        gi_rate = (xg + xa) / gw_played
        bonus = gi_rate * w['mid_gi'] + ict / w['mid_ict']
    elif pos == 4: # FWD
        gi_rate = (xg + xa) / gw_played
        bonus = gi_rate * w['fwd_gi'] + ict / w['fwd_ict']

    # Dream Team frequency bonus:
    # Players who appear in the Dream Team often have explosive ceiling.
    # Reward them slightly to surface big-game threats in squad selection.
    dt_count  = getattr(player, 'dream_team_count', 0) or 0
    dt_bonus  = min(dt_count / season_gws, 0.5) * w['dt_scale']

    # Fixture difficulty adjustment
    fixture_mults = _get_fixture_multipliers()
    team_id = getattr(player.team, 'fpl_id', None) if player.team else None
    att_mult, def_mult = fixture_mults.get(team_id, (1.0, 1.0)) if team_id else (1.0, 1.0)

    if pos in (3, 4):   # MID, FWD — attacking bonus scaled by opponent defence
        bonus *= att_mult
        base_score *= att_mult
    elif pos in (1, 2): # GK, DEF — defensive bonus scaled by opponent attack
        bonus *= def_mult
        base_score *= def_mult

    score = (base_score + bonus) * play_prob + dt_bonus

    # Availability: use chance_of_playing_next_round when available (0/25/50/75/100)
    cop = player.chance_of_playing_next_round
    if cop is not None:
        score *= (cop / 100)
    elif player.status == 'd':
        score *= 0.5
    elif player.status not in ('a',):
        score *= 0.0

    # FIX 5: Apply global calibration scalar (corrects systematic over-prediction)
    score *= w.get('cal_scalar', 0.78)

    return round(max(score, 0.0), 2)


def captain_score(player) -> float:
    """
    Score optimised for captain selection — prioritises upside over reliability.
    Captain picks should target players who can produce 15-20 pt explosions,
    not just consistent 5-7 pt performers.

    Combines:
      - Recent form (hot streaks = captaincy value)
      - Season ceiling: best recent GW score as proxy for max potential
      - Dream Team frequency: elite players appear there in big games
      - xG/xA involvement rate: attacking threat for blanket-high scoring
      - Chance of playing (penalise doubts)
    """
    pos       = player.position
    form      = float(player.form or 0)
    ppg       = float(player.points_per_game or 0)
    total_pts = player.total_points or 0
    mins      = player.minutes or 0
    xg        = float(player.expected_goals or 0)
    xa        = float(player.expected_assists or 0)
    ict       = float(player.ict_index or 0)
    dt_count  = getattr(player, 'dream_team_count', 0) or 0

    season_gws  = _get_season_gws()
    appearances = (total_pts / ppg) if ppg > 0.5 else max(mins / 90, 0.5)
    gw_played   = max(appearances, 1)
    regularity  = min(appearances / season_gws, 1.0)
    avg_mins    = mins / gw_played
    play_prob   = min(avg_mins / 90, 1.0) * regularity

    # Attacking involvement rate per game
    gi_rate = (xg + xa) / gw_played

    # Dream Team frequency as a ceiling signal
    dt_rate = dt_count / season_gws

    # Captain score: form-heavy + involvement + ceiling bonus
    score = (
        form      * 0.45 +           # recent form is the biggest captain signal
        ppg       * 0.25 +           # season consistency
        gi_rate   * 4.0  +           # goal/assist involvement per game
        dt_rate   * 10.0 +           # dream-team ceiling (high scorer potential)
        ict       / 250              # overall attacking threat index
    ) * play_prob

    # Fixture difficulty — captain upside scales with attacking opportunity
    fixture_mults = _get_fixture_multipliers()
    team_id = getattr(player.team, 'fpl_id', None) if player.team else None
    att_mult, def_mult = fixture_mults.get(team_id, (1.0, 1.0)) if team_id else (1.0, 1.0)
    if pos in (3, 4):
        score *= att_mult
    elif pos in (1, 2):
        score *= def_mult

    # Availability
    cop = player.chance_of_playing_next_round
    if cop is not None:
        score *= (cop / 100)
    elif player.status == 'd':
        score *= 0.5
    elif player.status not in ('a',):
        score *= 0.0

    return round(max(score, 0.0), 2)


# ─── Keras model loader ───────────────────────────────────────────────────────

def _load_keras_model(path: Path):
    try:
        import tensorflow as tf
        return tf.keras.models.load_model(str(path))
    except Exception as e:
        logger.error(f"Failed to load Keras model from {path}: {e}")
        return None


def _load_scaler(path: Path):
    try:
        import joblib
        return joblib.load(str(path))
    except Exception as e:
        logger.error(f"Failed to load scaler from {path}: {e}")
        return None


def get_model(position: str, model_type: str):
    key = f"{position}_{model_type}"
    if key in _model_cache:
        return _model_cache[key]
    artifacts = _artifacts_path()
    model_dir  = artifacts / f"{position}_{model_type}"
    model_path = model_dir / 'model.keras'
    scaler_path = model_dir / 'scaler.pkl'
    if not model_path.exists():
        _model_cache[key] = (None, None)
        return (None, None)
    model  = _load_keras_model(model_path)
    scaler = _load_scaler(scaler_path) if scaler_path.exists() else None
    _model_cache[key] = (model, scaler)
    return (model, scaler)


def build_feature_sequence(
    gw_stats_qs,
    model_type: str,
    player_fpl_id: int | None = None,
    position: str | None = None,
) -> 'np.ndarray | None':
    """
    Build a (SEQUENCE_LENGTH, n_features) input array for the LSTM/GRU/TFT model.

    Slot-filling priority (earliest slot first):
      1. Zero padding              — only when both current + prev season are insufficient
      2. Previous-season tail      — last GWs of 2024-25 from vaastav CSV
      3. Current-season GW stats   — from PlayerGameweekStats queryset (most recent)

    If all slots would be zero (completely unknown player) returns None
    so the caller falls back to the stat-based heuristic.
    """
    features = _get_features(position or 'MID', model_type)
    n_feat   = len(features)

    # ── Current season rows (ordered earliest → latest) ───────────────────────
    records = list(gw_stats_qs.order_by('-gameweek__fpl_id')[:SEQUENCE_LENGTH])
    current_rows: list[list[float]] = [
        [float(getattr(stat, f, None) or 0) for f in features]
        for stat in reversed(records)
    ]
    n_current = len(current_rows)

    if n_current >= SEQUENCE_LENGTH:
        # Full window — no fallback needed
        return np.array(current_rows, dtype=np.float32)

    # ── Previous-season fallback ───────────────────────────────────────────────
    prev_rows: list[list[float]] = []
    n_needed = SEQUENCE_LENGTH - n_current

    if player_fpl_id is not None:
        prev_cache = _load_prev_season_tail()
        all_prev   = prev_cache.get(player_fpl_id, [])
        if all_prev:
            # Extract only the features needed for this position/model_type
            candidate = [
                [row_dict.get(f, 0.0) for f in features]
                for row_dict in all_prev
            ]
            prev_rows = candidate[-n_needed:]   # most-recent n_needed of prev season

    # ── Zero-pad any remaining gap ─────────────────────────────────────────────
    n_zeros   = n_needed - len(prev_rows)
    zero_rows = [[0.0] * n_feat for _ in range(n_zeros)]

    all_rows = zero_rows + prev_rows + current_rows

    # If every row is all-zeros → no usable data; return None → stat fallback
    if all(v == 0.0 for row in all_rows for v in row):
        return None

    return np.array(all_rows, dtype=np.float32)


def predict_player(player, gw_stats_qs, model_type: str | None = None) -> float:
    """
    Returns predicted GW points. Uses ML model when available,
    otherwise falls back to the stat-based heuristic.

    After scoring, applies a position-specific calibration multiplier
    (actual/predicted ratio learned from GW history) to correct systematic
    over-prediction bias.
    """
    position_name = POSITION_MAP.get(player.position, 'MID')
    if model_type is None:
        model_type = BEST_MODEL_PER_POSITION.get(position_name, 'lstm_base')

    model, scaler = get_model(position_name, model_type)

    if model is None:
        # No ML artifact — stat-based fallback (already applies cal_scalar internally)
        return _fallback_score(player)

    seq = build_feature_sequence(
        gw_stats_qs, model_type,
        player_fpl_id=player.fpl_id,
        position=position_name,
    )
    if seq is None:
        return _fallback_score(player)

    if scaler is not None:
        n = seq.shape[1]
        seq = scaler.transform(seq.reshape(-1, n)).reshape(1, SEQUENCE_LENGTH, n)
    else:
        seq = seq.reshape(1, SEQUENCE_LENGTH, seq.shape[1])

    pred = model.predict(seq, verbose=0)
    raw_score = float(pred[0][0])

    # Apply position-specific calibration multiplier to correct over-prediction bias.
    # Only applied to ML model output — the fallback already applies cal_scalar.
    cal = compute_calibration_multipliers()
    multiplier = cal.get(position_name, 1.0)
    calibrated = raw_score * multiplier

    return round(max(calibrated, 0.0), 2)


def predict_all_players_for_gw(position_filter: list[int] | None = None) -> list[dict]:
    from fpl.models import Player, PlayerGameweekStats
    players = Player.objects.select_related('team').all()
    if position_filter:
        players = players.filter(position__in=position_filter)
    results = []
    for player in players:
        gw_stats = PlayerGameweekStats.objects.filter(player=player).order_by('-gameweek__fpl_id')
        pos_name   = POSITION_MAP.get(player.position, 'MID')
        model_type = BEST_MODEL_PER_POSITION.get(pos_name, 'lstm_base')
        pred = predict_player(player, gw_stats, model_type)
        results.append({
            'player_id':        player.fpl_id,
            'web_name':         player.web_name,
            'position':         pos_name,
            'team':             player.team.short_name if player.team else '',
            'price':            player.price,
            'predicted_points': pred,
            'model':            'fallback' if not _models_available() else model_type,
        })
    results.sort(key=lambda x: x['predicted_points'], reverse=True)
    return results
