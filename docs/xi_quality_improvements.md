# XI Quality Improvements

This document tracks changes made to the FPL Best XI selection pipeline and the measured impact of each layer.

---

## Best XI Quality Improvements — Results

## Layer-by-Layer Impact Analysis (GW30 test)

### Layer 1 — Availability Filter
- GW30 result: No players filtered (all fit)
- Purpose confirmed: prevents injured/doubtful players entering the XI
- Will activate automatically when players have chance_of_playing < 30%

### Layer 2 — Fixture Weighting
- Bug found: fixture lookup was matching finished fixtures (GW30 was complete),
  returning FDR=3 default for all players
- Fix: changed query to filter `finished=False`, `event >= current_gw`
- After fix: Haaland/Gühi/Semenyo correctly show FDR=4 (tough fixture);
  Arsenal/Brentford players show FDR=3 (neutral)
- Impact: Haaland predicted_points 5.8 → adjusted_points 5.2 (−10.3%)

### Layer 3 — Dream Team Captain Bonus
- Most impactful layer this GW
- Captain changed: Haaland → Semenyo
- Evidence: Semenyo 4 dream team apps + 1 captain finish
  vs Haaland 9 dream team apps + 0 captain finishes in squad
- Combined with FDR penalty on Haaland: optimizer correctly avoided
  blindly picking the highest raw-points player

### Layer 4 — Groq Reasoning
- Initial issue: contradictory output ("Semenyo good but consider Haaland")
- Fix: added explicit system prompt rule — commit to captain decision,
  do not hedge
- After fix: decisive reasoning with fixture context
- GW30: approved optimizer XI, no swaps suggested, team_rating=strong

### Root Cause of Original Problem
The original system picked Haaland every week because:
1. No availability filter — injured players could enter
2. No fixture weighting — FDR not applied to predictions
3. No historical captain data — pure points maximisation
4. No qualitative check — no reasoning layer

All 4 root causes now addressed.
