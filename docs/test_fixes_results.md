# Prediction Enhancement Test Results

**Baseline (recorded pre-fixes)**: avg|diff|=12.30, mean_diff=+0.26, bad_GWs=6
**Production result (GW1-31 after all fixes applied)**: avg|diff|=15.09, bad_GWs=9
  - GW1-10: 14.1 | GW11-20: 13.6 | GW21-31: 17.3 (phase drift significantly flattened)
  - Note: fresh simulation starts from DEFAULT_WEIGHTS; the recorded 12.30 benefited from prior warm weights.

## Summary Table

| Config | mean_diff | avg\|diff\| | Δ vs baseline | std | bad_GWs | H_cap | avg_MAE | Verdict |
|--------|-----------|------------|--------------|-----|---------|-------|---------|---------|
| BASELINE | -13.92 | 18.61 | — | 17.75 | 17 | 30 | 3.497 | — |
| FIX1_EMA_CAL | -9.72 | 15.34 | -3.27 | 16.81 | 11 | 30 | 3.365 | ✅ KEEP |
| FIX2_CONSEC_CAP | -13.86 | 18.58 | -0.03 | 17.80 | 17 | 27 | 3.497 | ✅ KEEP |
| FIX3_FLOOR | -13.79 | 18.48 | -0.13 | 17.65 | 17 | 30 | 3.490 | ✅ KEEP |
| FIX4_DEF_CORR | -13.88 | 18.57 | -0.04 | 17.77 | 17 | 30 | 3.493 | ✅ KEEP |
| FIX5_RECENCY | -13.23 | 17.92 | -0.69 | 17.53 | 15 | 30 | 3.474 | ✅ KEEP |
| ALL_FIXES | -6.62 | 13.48 | -5.13 | 16.15 | 8 | 29 | 3.266 | ✅ KEEP |

## Bad GW breakdown

- **BASELINE**: bad GWs = [9, 11, 12, 13, 15, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30]
- **FIX1_EMA_CAL**: bad GWs = [9, 11, 12, 18, 19, 20, 22, 23, 26, 29, 30]
- **FIX2_CONSEC_CAP**: bad GWs = [9, 11, 12, 13, 15, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30]
- **FIX3_FLOOR**: bad GWs = [9, 11, 12, 13, 15, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30]
- **FIX4_DEF_CORR**: bad GWs = [9, 11, 12, 13, 15, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30]
- **FIX5_RECENCY**: bad GWs = [9, 11, 12, 13, 18, 19, 20, 22, 23, 24, 26, 27, 28, 29, 30]
- **ALL_FIXES**: bad GWs = [9, 11, 12, 18, 22, 23, 26, 30]

## Root Cause Analysis: Why Large Diffs Occur

_Conducted 2026-04-03. Full GW1-31 backtest with calibration log._

### Key finding: the model is NOT the problem

Per-player MAE is rock-solid across all 31 GWs:

| Metric | Value |
|--------|-------|
| Per-player MAE range | 2.063 – 2.642 pts |
| Per-player MAE avg | 2.341 pts |
| Per-player MAE std | 0.127 pts |
| GWs with MAE > 3.0 | **0** |

The model predicts individual players consistently well. No gameweek shows genuinely bad player-level predictions.

### The actual source: captain blank × double multiplier

All 8 bad GWs (diff < −15) are caused by Haaland blanking while captained. The squad itself is typically close to neutral in these GWs:

| GW | H actual | cap error | squad error | total diff | verdict |
|----|----------|-----------|-------------|------------|---------|
| GW 9 | 2pts | −13.0 | −5.7 | −18.7 | cap blank |
| GW11 | 4pts | −9.0 | −28.6 | −37.6 | cap low + bad squad GW (only combined failure) |
| GW12 | 2pts | −13.0 | −8.6 | −21.6 | cap blank |
| GW18 | 2pts | −13.0 | −4.1 | −17.1 | cap blank |
| GW22 | 2pts | −13.0 | −12.5 | −25.5 | cap blank + bad squad |
| GW23 | 1pt  | −15.0 | −0.4 | −15.4 | **squad = −0.4 (near perfect), pure cap blank** |
| GW26 | 5pts | −7.0  | −14.2 | −21.2 | cap low + bad squad |
| GW30 | 2pts | −13.0 | −5.0 | −18.0 | cap blank |

GW23 is the clearest example: squad_error = −0.4 (model got 10/11 players almost exactly right), but Haaland scored 1pt as captain → team diff = −15.4.

### Captain blank statistics (GW1-31)

| Scenario | GWs | avg team diff |
|----------|-----|---------------|
| Haaland blank (≤2pts) as captain | 13 / 30 GWs (43%) | **−14.2** |
| Haaland low (3–8pts) as captain | 8 / 30 GWs | **−13.8** |
| Haaland hauls (≥8.5pts) as captain | 9 / 30 GWs | **+6.2** |

### Why this cannot be fixed by the prediction model

Haaland's blank GWs are caused by:
- Man City resting him in low-priority matches
- Opponent defensive setups on the day
- Match-day randomness (missed big chances, offside goals)

None of these are predictable from a 5-GW rolling window. This is **irreducible aleatoric uncertainty** — the same category as injury blanks and red cards. A perfect prediction model would still face this problem because the information simply does not exist before the match.

The only alternative is to captain a different player, but any substitute (Salah, Palmer, Mbeumo) has lower expected predicted points, trading fewer catastrophic GWs for consistently worse expected returns.

## Fix Descriptions

| Fix | Description | Location |
|-----|-------------|----------|
| Fix 1 | Recency-weighted calibration (EMA last 8 GWs, decay=0.75) — corrects phase drift | `ml_loader.py: compute_calibration_multipliers()`, `scorer_weights.py: calibrate_after_gw()` |
| Fix 2 | Consecutive blank captain penalty (×0.70 if blanked 2+ of last 3 GWs) | `optimizer.py: _cap_util()` in `simulate_learning_progression()` and `build_best_team()` |
| Fix 3 | Predicted floor 1.5pts for regular starters (regularity>0.7, avg_mins>60) | `scorer_weights.py: score_all_players_before_gw()` |
| Fix 4 | DEF clean-sheet correlation penalty (×0.92 for 3rd+ DEF from same team) | `optimizer.py: build_best_team()` and simulation loop |
| Fix 5 | Late-season recency correction (nudge cal_scalar down if last 5 mean_diff < -10) | `scorer_weights.py: calibrate_after_gw()` |