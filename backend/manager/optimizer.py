"""
FPL Best-XI Optimizer
======================
Uses PuLP linear programming to select the optimal starting 11 from a 15-player
squad, maximising total predicted points subject to FPL formation constraints.

Layers applied (in order):
  1. Availability Filter  — removes players with chance_of_playing < 30%
  2. Fixture Weight        — scales predicted_points by FDR before LP optimisation
  3. Dream Team Bonus      — adds captaincy signal from historical dream team data

Public API
----------
    get_best_xi(squad, predictions) -> dict
    filter_available_players(players)  -> list
    apply_fixture_weight(players)      -> list
"""

import logging
from typing import Optional

try:
    import pulp
    _PULP_AVAILABLE = True
except ImportError:
    _PULP_AVAILABLE = False

logger = logging.getLogger(__name__)

# Position codes
GK, DEF, MID, FWD = 'GK', 'DEF', 'MID', 'FWD'

# Formation bounds (min, max starters per outfield position)
_BOUNDS = {
    DEF: (3, 5),
    MID: (2, 5),
    FWD: (1, 3),
}

# ── Layer 2: FDR multipliers ──────────────────────────────────────────────────

FDR_MULTIPLIER = {
    1: 1.15,
    2: 1.08,
    3: 1.00,
    4: 0.90,
    5: 0.80,
}


# ── Layer 1: Availability filter ──────────────────────────────────────────────

def filter_available_players(players: list[dict]) -> list[dict]:
    """
    Remove players unlikely to play this GW.
    chance_of_playing_this_round == None  →  no injury news → keep
    chance_of_playing_this_round >= 30   →  keep
    chance_of_playing_this_round <  30   →  remove (log who was filtered)
    """
    available = []
    for p in players:
        chance = p.get('chance_of_playing_this_round')
        if chance is None or chance >= 30:
            available.append(p)
        else:
            logger.info(
                "Layer1 filtered out %s — chance_of_playing=%s%%",
                p.get('name', p.get('id')), chance,
            )
    return available


# ── Layer 2: Fixture-weighted predictions ────────────────────────────────────

def apply_fixture_weight(players: list[dict]) -> list[dict]:
    """
    Scale predicted_points by fixture difficulty and store as adjusted_points.
    FDR 1-2 = easy (boost), FDR 4-5 = hard (penalty).
    Also stores fdr_multiplier so the frontend can display ↑/↓ arrows.
    """
    for p in players:
        fdr = p.get('fixture_difficulty', 3)
        try:
            fdr = int(fdr)
        except (TypeError, ValueError):
            fdr = 3
        multiplier = FDR_MULTIPLIER.get(fdr, 1.0)
        p['adjusted_points'] = round(float(p.get('predicted_points', 0)) * multiplier, 3)
        p['fdr_multiplier'] = multiplier
    return players


# ── Layer 3: Captain scoring with dream team bonus ────────────────────────────

def _captain_score(p: dict) -> float:
    """
    Score used to rank starting XI players for captaincy.
    Doubles the optimisation score and adds a dream team captaincy signal.
    """
    base = p.get('adjusted_points', p.get('predicted_points', 0))
    dream_bonus = float(p.get('captain_appearances', 0)) * 0.5
    return float(base) * 2 + dream_bonus


# ── Fallback greedy (no PuLP) ─────────────────────────────────────────────────

def _fallback_best_xi(squad: list[dict]) -> dict:
    """Greedy fallback when PuLP is not installed."""
    key = lambda p: -p.get('adjusted_points', p.get('predicted_points', 0))
    gks  = sorted([p for p in squad if p['position'] == GK],  key=key)
    defs = sorted([p for p in squad if p['position'] == DEF], key=key)
    mids = sorted([p for p in squad if p['position'] == MID], key=key)
    fwds = sorted([p for p in squad if p['position'] == FWD], key=key)

    starters = [gks[0]] + defs[:3] + mids[:2] + fwds[:1]
    remaining = (gks[1:] + defs[3:] + mids[2:] + fwds[1:])
    remaining.sort(key=key)
    starters += remaining[:4]
    bench = [p for p in squad if p['id'] not in {s['id'] for s in starters}]
    return _build_result(starters, bench)


# ── Result builder ────────────────────────────────────────────────────────────

def _build_result(starters: list[dict], bench: list[dict]) -> dict:
    """Build the return dict including captain / vice-captain (Layer 3 scoring)."""
    starters_sorted = sorted(starters, key=lambda p: -_captain_score(p))
    captain      = starters_sorted[0] if starters_sorted else None
    vice_captain = starters_sorted[1] if len(starters_sorted) > 1 else None

    def _slim(p: dict) -> dict:
        return {
            'id':               p['id'],
            'name':             p['name'],
            'position':         p['position'],
            'team':             p.get('team', ''),
            'price':            p.get('price', 0),
            'predicted_points': p.get('predicted_points', 0),
            'adjusted_points':  p.get('adjusted_points', p.get('predicted_points', 0)),
            'fdr_multiplier':   p.get('fdr_multiplier', 1.0),
            'fixture_difficulty': p.get('fixture_difficulty', 3),
            'dream_team_appearances': p.get('dream_team_appearances', 0),
            'captain_appearances': p.get('captain_appearances', 0),
            'chance_of_playing': p.get('chance_of_playing_this_round'),
            'photo_code':       p.get('photo_code'),
        }

    pos_counts = {}
    for p in starters:
        pos_counts[p['position']] = pos_counts.get(p['position'], 0) + 1

    n_def = pos_counts.get(DEF, 0)
    n_mid = pos_counts.get(MID, 0)
    n_fwd = pos_counts.get(FWD, 0)
    formation = f"1-{n_def}-{n_mid}-{n_fwd}"

    return {
        'starting_xi':  [_slim(p) for p in starters],
        'bench':        [_slim(p) for p in bench],
        'formation':    formation,
        'captain':      {'id': captain['id'], 'name': captain['name']} if captain else None,
        'vice_captain': {'id': vice_captain['id'], 'name': vice_captain['name']} if vice_captain else None,
    }


# ── Main public function ──────────────────────────────────────────────────────

def get_best_xi(squad: list[dict], predictions: list[dict] = None) -> dict:
    """
    Select the optimal starting 11 from a 15-player squad using LP.

    Applies 3 layers before solving:
      L1 — availability filter (removes chance_of_playing < 30%)
      L2 — fixture weighting  (adjusted_points = predicted_points * FDR_MULTIPLIER)
      L3 — dream team captain bonus in _build_result()

    Parameters
    ----------
    squad : list[dict]
        15 players, each with keys:
            id, name, position ('GK'|'DEF'|'MID'|'FWD'),
            team, price, predicted_points,
            chance_of_playing_this_round (None or 0-100),
            fixture_difficulty (1-5),
            dream_team_appearances (int),
            captain_appearances (int)
    predictions : list[dict]
        Ignored here; kept for API compatibility.

    Returns
    -------
    dict with keys:
        starting_xi  : list[dict]  — 11 players
        bench        : list[dict]  — 4 players
        formation    : str         — e.g. "1-4-4-2"
        captain      : dict        — {id, name}
        vice_captain : dict        — {id, name}
    """
    if not squad:
        raise ValueError("Squad is empty.")

    # ── Layer 1: filter unavailable ──────────────────────────────────────────
    n_before = len(squad)
    available_squad = filter_available_players(squad)
    n_filtered = n_before - len(available_squad)
    if n_filtered:
        logger.info("Layer1: filtered %d unavailable player(s) from squad", n_filtered)

    # If filtering leaves too few to form a valid XI, use full squad
    if len(available_squad) < 11:
        logger.warning(
            "Too few available players after filter (%d) — using full squad",
            len(available_squad),
        )
        available_squad = squad

    # ── Layer 2: apply fixture weighting ─────────────────────────────────────
    available_squad = apply_fixture_weight(available_squad)

    if not _PULP_AVAILABLE:
        logger.warning("PuLP not installed — using greedy fallback for best-XI.")
        return _fallback_best_xi(available_squad)

    n = len(available_squad)
    indices = list(range(n))

    # ── LP problem ────────────────────────────────────────────────────────────
    prob = pulp.LpProblem("FPL_Best_XI", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x_{i}", cat='Binary') for i in indices]

    # Objective: maximise FIXTURE-WEIGHTED points (Layer 2)
    prob += pulp.lpSum(
        x[i] * float(available_squad[i].get('adjusted_points', 0))
        for i in indices
    )

    # Exactly 11 starters
    prob += pulp.lpSum(x) == 11

    # Exactly 1 GK starts
    gk_idx = [i for i, p in enumerate(available_squad) if p['position'] == GK]
    prob += pulp.lpSum(x[i] for i in gk_idx) == 1

    # Min/max per outfield position
    for pos, (lo, hi) in _BOUNDS.items():
        pos_idx = [i for i, p in enumerate(available_squad) if p['position'] == pos]
        prob += pulp.lpSum(x[i] for i in pos_idx) >= lo
        prob += pulp.lpSum(x[i] for i in pos_idx) <= hi

    solver = pulp.PULP_CBC_CMD(msg=0)
    prob.solve(solver)

    if pulp.LpStatus[prob.status] != 'Optimal':
        logger.warning("LP did not reach optimal — falling back to greedy.")
        return _fallback_best_xi(available_squad)

    starter_ids = {available_squad[i]['id'] for i in indices if pulp.value(x[i]) == 1}
    starters = [p for p in available_squad if p['id'] in starter_ids]
    bench    = [p for p in available_squad if p['id'] not in starter_ids]

    # Also include bench players from original squad that were filtered out
    available_ids = {p['id'] for p in available_squad}
    filtered_out  = [p for p in squad if p['id'] not in available_ids]
    bench += filtered_out

    bench.sort(key=lambda p: -p.get('adjusted_points', p.get('predicted_points', 0)))

    # ── Layer 3: captain via dream team bonus (in _build_result) ─────────────
    return _build_result(starters, bench)
