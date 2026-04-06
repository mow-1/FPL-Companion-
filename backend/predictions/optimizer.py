"""
FPL Best Team Optimizer.
Rules: 2 GK, 5 DEF, 5 MID, 3 FWD · £100m budget · max 3/club
Starting XI: 1 GK + valid formation (3-4-3, 4-3-3, 4-4-2, 4-5-1, 5-4-1, 5-3-2, 5-2-3, 3-5-2)
Bench: 1 GK + 3 outfield (ordered for auto-sub)
"""
from __future__ import annotations

VALID_FORMATIONS = [(3,4,3),(3,5,2),(4,3,3),(4,4,2),(4,5,1),(5,2,3),(5,3,2),(5,4,1)]
# Full squad requirements
SQUAD_REQS   = {1: 2, 2: 5, 3: 5, 4: 3}
MAX_PER_CLUB = 3


def _compute_min_prices(candidates: list[dict]) -> dict[int, float]:
    """Minimum available price per position from the actual candidate pool."""
    mins: dict[int, float] = {}
    for p in candidates:
        pos = p['position']
        if pos not in mins or p['price'] < mins[pos]:
            mins[pos] = p['price']
    fallback = {1: 3.8, 2: 3.7, 3: 4.2, 4: 4.1}
    return {pos: mins.get(pos, fallback[pos]) for pos in range(1, 5)}


def _pick_xi_for_formation(
    candidates_by_pos: dict,
    n_def: int, n_mid: int, n_fwd: int,
    xi_budget: float,
    min_prices: dict,
) -> list[dict] | None:
    """
    Greedily pick the best possible XI for a given formation within xi_budget.
    Iterates over ALL positions together sorted by predicted_points descending
    so budget is spent on the globally highest-value players, not position-by-position.
    Returns the 11-player list or None if infeasible.
    """
    slots   = {1: 1, 2: n_def, 3: n_mid, 4: n_fwd}
    counts  = {1: 0, 2: 0, 3: 0, 4: 0}
    clubs   = {}
    picked  = []
    spent   = 0.0

    # All candidates eligible for this formation, sorted by predicted pts desc
    pool = sorted(
        [p for pos, players in candidates_by_pos.items()
         for p in players if slots.get(pos, 0) > 0],
        key=lambda x: x['predicted_points'], reverse=True,
    )

    for p in pool:
        pos = p['position']
        if counts[pos] >= slots[pos]:
            continue
        if clubs.get(p['team_id'], 0) >= MAX_PER_CLUB:
            continue

        # Reserve budget for remaining unfilled slots
        new_counts = {**counts, pos: counts[pos] + 1}
        reserve = sum(
            max(slots[p2] - new_counts[p2], 0) * min_prices[p2]
            for p2 in slots
        )
        if spent + p['price'] + reserve > xi_budget + 0.05:
            continue

        picked.append(p)
        counts[pos] += 1
        clubs[p['team_id']] = clubs.get(p['team_id'], 0) + 1
        spent += p['price']

        if len(picked) == 11:
            break

    return picked if len(picked) == 11 else None


def _fill_bench(
    candidates_by_pos: dict,
    bench_slots: dict,       # {pos: count_needed}
    xi_ids: set,
    xi_club_counts: dict,
    bench_budget: float,
    min_prices: dict,
    fallback_pool: list[dict] | None = None,
) -> list[dict]:
    """
    Fill the bench with the cheapest legal players.
    Sorted by price ascending so the most budget stays available for the XI.
    If the main pool cannot fill all slots (club constraint or budget), any
    remaining slots are filled from fallback_pool (broader set of players
    including injured/suspended) at the lowest possible price.
    """
    clubs  = dict(xi_club_counts)
    counts = {pos: 0 for pos in range(1, 5)}
    bench  = []
    spent  = 0.0
    picked_ids = set(xi_ids)

    # Sort cheapest first — bench players are fillers
    pool = sorted(
        [p for players in candidates_by_pos.values() for p in players
         if p['fpl_id'] not in xi_ids],
        key=lambda x: x['price'],
    )

    for p in pool:
        pos = p['position']
        if counts[pos] >= bench_slots.get(pos, 0):
            continue
        if clubs.get(p['team_id'], 0) >= MAX_PER_CLUB:
            continue

        new_counts = {**counts, pos: counts[pos] + 1}
        reserve = sum(
            max(bench_slots.get(p2, 0) - new_counts[p2], 0) * min_prices[p2]
            for p2 in bench_slots
        )
        if spent + p['price'] + reserve > bench_budget + 0.05:
            continue

        bench.append(p)
        counts[pos] += 1
        clubs[p['team_id']] = clubs.get(p['team_id'], 0) + 1
        spent += p['price']
        picked_ids.add(p['fpl_id'])

        if sum(counts.values()) == sum(bench_slots.values()):
            break

    # ── Fallback: fill any remaining slots from the broader pool ────────────
    # This handles cases where club constraints or budget exhaust the main pool.
    if sum(counts.values()) < sum(bench_slots.values()) and fallback_pool:
        fb_sorted = sorted(
            [p for p in fallback_pool if p['fpl_id'] not in picked_ids],
            key=lambda x: x['price'],
        )
        for p in fb_sorted:
            pos = p['position']
            if counts[pos] >= bench_slots.get(pos, 0):
                continue
            if clubs.get(p['team_id'], 0) >= MAX_PER_CLUB:
                continue
            bench.append(p)
            counts[pos] += 1
            clubs[p['team_id']] = clubs.get(p['team_id'], 0) + 1
            picked_ids.add(p['fpl_id'])
            if sum(counts.values()) == sum(bench_slots.values()):
                break

    # Order bench: GK first, then outfield best→worst (best sub comes on first)
    bench_gk  = [p for p in bench if p['position'] == 1]
    bench_out = sorted([p for p in bench if p['position'] != 1],
                       key=lambda x: x['predicted_points'], reverse=True)
    return bench_gk + bench_out


def _build_squad(candidates: list[dict], budget: float, fallback_pool: list[dict] | None = None):
    """
    Two-phase squad builder that prioritises XI quality:

    Phase 1 — XI optimisation:
      For each valid formation, compute the minimum bench cost (cheapest
      available players to fill bench slots), then use the remaining budget
      entirely on picking the best possible XI.  The formation that yields
      the highest total XI predicted points wins.

    Phase 2 — Bench fill:
      Fill bench slots with the cheapest legal players not already in the XI.

    This ensures budget is concentrated on the starting 11, not wasted on
    expensive bench players who rarely contribute.
    """
    min_prices      = _compute_min_prices(candidates)
    candidates_by_pos = {
        pos: sorted([p for p in candidates if p['position'] == pos],
                    key=lambda x: x['predicted_points'], reverse=True)
        for pos in range(1, 5)
    }

    best_xi       = None
    best_score    = -1.0
    best_formation = None

    for (n_def, n_mid, n_fwd) in VALID_FORMATIONS:
        # Bench slots required by this formation
        bench_slots = {1: 1, 2: 5 - n_def, 3: 5 - n_mid, 4: 3 - n_fwd}
        bench_min   = sum(bench_slots[pos] * min_prices[pos] for pos in bench_slots)
        xi_budget   = budget - bench_min

        xi = _pick_xi_for_formation(
            candidates_by_pos, n_def, n_mid, n_fwd, xi_budget, min_prices
        )
        if xi is None:
            continue

        # Captain is the highest-predicted XI player; score includes his 2×
        xi_sorted = sorted(xi, key=lambda x: x['predicted_points'], reverse=True)
        cap_id    = xi_sorted[0]['fpl_id']
        score     = sum(
            p['predicted_points'] * (2 if p['fpl_id'] == cap_id else 1)
            for p in xi
        )
        if score > best_score:
            best_score    = score
            best_xi       = xi
            best_formation = (n_def, n_mid, n_fwd)

    if best_xi is None:
        return None, None

    n_def, n_mid, n_fwd = best_formation
    bench_slots  = {1: 1, 2: 5 - n_def, 3: 5 - n_mid, 4: 3 - n_fwd}
    xi_ids       = {p['fpl_id'] for p in best_xi}
    xi_clubs     = {}
    for p in best_xi:
        xi_clubs[p['team_id']] = xi_clubs.get(p['team_id'], 0) + 1

    xi_cost      = sum(p['price'] for p in best_xi)
    bench_budget = budget - xi_cost

    bench = _fill_bench(
        candidates_by_pos, bench_slots, xi_ids, xi_clubs, bench_budget, min_prices,
        fallback_pool=fallback_pool,
    )
    return best_xi, bench


def _get_fixtures(gameweek) -> dict[int, str]:
    """Return {team_id: 'OPP (H/A)'} for the given gameweek.
    Teams with a blank GW (no fixture) fall back to their next upcoming fixture,
    labelled 'OPP (H) GW{n}' so blank-GW players aren't shown as 'TBC'.
    """
    try:
        from fpl.models import Fixture, Team
        fixtures = Fixture.objects.filter(gameweek=gameweek).select_related('team_h', 'team_a')
        out: dict[int, str] = {}
        for f in fixtures:
            if f.team_h_id and f.team_a:
                out[f.team_h_id] = f"{f.team_a.short_name} (H)"
            if f.team_a_id and f.team_h:
                out[f.team_a_id] = f"{f.team_h.short_name} (A)"

        # For teams with a blank GW, find their next upcoming fixture
        if gameweek:
            missing = set(Team.objects.values_list('id', flat=True)) - set(out.keys())
            if missing:
                upcoming = (
                    Fixture.objects
                    .filter(finished=False, gameweek__fpl_id__gt=gameweek.fpl_id)
                    .select_related('team_h', 'team_a', 'gameweek')
                    .order_by('gameweek__fpl_id', 'kickoff_time')
                )
                for f in upcoming:
                    if f.team_h_id in missing and f.team_h and f.team_a:
                        out[f.team_h_id] = f"{f.team_a.short_name} (H) GW{f.gameweek.fpl_id}"
                        missing.discard(f.team_h_id)
                    if f.team_a_id in missing and f.team_h and f.team_a:
                        out[f.team_a_id] = f"{f.team_h.short_name} (A) GW{f.gameweek.fpl_id}"
                        missing.discard(f.team_a_id)
                    if not missing:
                        break
        return out
    except Exception:
        return {}


def _get_fdr_map(gameweek) -> dict[int, int]:
    """Return {team_id: fdr_int} for the given gameweek (1=easy … 5=hard)."""
    try:
        from fpl.models import Fixture
        out: dict[int, int] = {}
        for f in Fixture.objects.filter(gameweek=gameweek):
            if f.team_h_id and f.team_h_difficulty:
                out[f.team_h_id] = int(f.team_h_difficulty)
            if f.team_a_id and f.team_a_difficulty:
                out[f.team_a_id] = int(f.team_a_difficulty)
        return out
    except Exception:
        return {}


_FDR_CAP_MULT = {1: 1.15, 2: 1.08, 3: 1.0, 4: 0.88, 5: 0.75}


def _to_pick(p: dict, is_starter: bool, bench_order: int | None,
             captain_id: int, vc_id: int, fixtures: dict,
             fdr_map: dict | None = None) -> dict:
    fdr = (fdr_map or {}).get(p['team_id'], 3)
    fdr_mult = _FDR_CAP_MULT.get(fdr, 1.0)
    dt_count = p.get('dream_team_count', 0)
    adjusted = round(p['predicted_points'] * fdr_mult, 2)
    return {
        **p,
        'fixture':               fixtures.get(p['team_id'], 'TBC'),
        'fixture_difficulty':    fdr,
        'adjusted_points':       adjusted,
        'captain_appearances':   dt_count,
        'dream_team_appearances': dt_count,
        'is_captain':            p['fpl_id'] == captain_id,
        'is_vice_captain':       p['fpl_id'] == vc_id,
        'is_starter':            is_starter,
        'bench_order':           bench_order,
    }


def _blank_rate_penalties(fpl_ids: list[int]) -> dict[int, float]:
    """
    Batch-fetch blank rates for all players and return a penalty multiplier per player.
    Blank = scoring <= 2 pts in a GW where they played (minutes > 0).
    Penalty applied only when blank_rate > 0.5: multiplier = 1 - (blank_rate - 0.5) * 0.4
    Returns {fpl_id: multiplier} — 1.0 (no penalty) for players below the threshold.
    """
    from fpl.models import PlayerGameweekStats
    from collections import defaultdict

    recent = (
        PlayerGameweekStats.objects
        .filter(player__fpl_id__in=fpl_ids, minutes__gt=0)
        .order_by('player__fpl_id', '-gameweek__fpl_id')
        .values('player__fpl_id', 'total_points')
    )

    pts_by_player: dict[int, list[int]] = defaultdict(list)
    for row in recent:
        pid = row['player__fpl_id']
        if len(pts_by_player[pid]) < 10:
            pts_by_player[pid].append(row['total_points'])

    penalties: dict[int, float] = {}
    for pid, pts in pts_by_player.items():
        if len(pts) >= 5:
            blank_rate = sum(1 for p in pts if p <= 2) / len(pts)
            if blank_rate > 0.5:
                penalties[pid] = round(1.0 - (blank_rate - 0.5) * 0.4, 4)
    return penalties


def build_best_team(budget: float = 100.0) -> dict:
    from fpl.models import Player, Gameweek
    from predictions.models import Prediction

    gw = (Gameweek.objects.filter(is_next=True).first()
          or Gameweek.objects.filter(is_current=True).first())

    fixtures = _get_fixtures(gw) if gw else {}
    fdr_map  = _get_fdr_map(gw)  if gw else {}

    if gw and Prediction.objects.filter(gameweek=gw).exists():
        preds = (Prediction.objects.filter(gameweek=gw)
                 .select_related('player__team')
                 .order_by('-predicted_points'))
        candidates = [
            {
                'fpl_id':           p.player.fpl_id,
                'web_name':         p.player.web_name,
                'team_name':        p.player.team.name if p.player.team else '',
                'team_short':       p.player.team.short_name if p.player.team else '',
                'team_id':          p.player.team_id or 0,
                'position':         p.player.position,
                'position_name':    p.player.get_position_display(),
                'price':            p.player.price,
                'predicted_points': p.predicted_points,
                'total_points':     p.player.total_points,
                'form':             float(p.player.form or 0),
                'status':           p.player.status,
                'photo_code':       p.player.code,
                'dream_team_count': p.player.dream_team_count or 0,
            }
            for p in preds
            if p.player.status in ('a', 'd') and p.player.now_cost > 0
        ]
    else:
        from predictions.ml_loader import _fallback_score
        players = Player.objects.select_related('team').filter(status__in=('a','d'), now_cost__gt=0)
        candidates = sorted([
            {
                'fpl_id':           pl.fpl_id,
                'web_name':         pl.web_name,
                'team_name':        pl.team.name if pl.team else '',
                'team_short':       pl.team.short_name if pl.team else '',
                'team_id':          pl.team_id or 0,
                'position':         pl.position,
                'position_name':    pl.get_position_display(),
                'price':            pl.price,
                'predicted_points': _fallback_score(pl),
                'total_points':     pl.total_points,
                'form':             float(pl.form or 0),
                'status':           pl.status,
                'photo_code':       pl.code,
                'dream_team_count': pl.dream_team_count or 0,
            }
            for pl in players
        ], key=lambda x: x['predicted_points'], reverse=True)

    # Deduplicate by fpl_id — keep highest predicted_points per player
    # (Prediction table can have duplicate rows if run_predictions was called multiple times)
    _seen: dict[int, dict] = {}
    for c in candidates:
        fid = c['fpl_id']
        if fid not in _seen or c['predicted_points'] > _seen[fid]['predicted_points']:
            _seen[fid] = c
    candidates = sorted(_seen.values(), key=lambda x: x['predicted_points'], reverse=True)

    # Apply blank-rate penalty — players who blank >50% of GWs get predicted_points reduced.
    # This discourages the optimizer from over-selecting boom/bust players (Haaland, Semenyo).
    blank_penalties = _blank_rate_penalties([c['fpl_id'] for c in candidates])
    for c in candidates:
        mult = blank_penalties.get(c['fpl_id'], 1.0)
        if mult < 1.0:
            c['predicted_points'] = round(c['predicted_points'] * mult, 2)
            c['blank_rate_penalty'] = mult

    # NEW FIX 4: DEF clean-sheet correlation penalty.
    # Apply ×0.92 to the 3rd+ DEF from the same team to discourage correlated CS risk.
    # Test result: avg|diff| −0.04 vs baseline.
    _def_team_count: dict[int, int] = {}
    for c in sorted([x for x in candidates if x['position'] == 2],
                    key=lambda x: x['predicted_points'], reverse=True):
        tid = c['team_id']
        _def_team_count[tid] = _def_team_count.get(tid, 0) + 1
        if _def_team_count[tid] >= 3:
            c['predicted_points'] = round(c['predicted_points'] * 0.92, 2)

    # Fallback pool: cheapest injured/suspended players to guarantee a full bench
    # when club constraints exhaust the main candidate pool.
    _all_players = Player.objects.select_related('team').filter(now_cost__gt=0).exclude(
        fpl_id__in=[c['fpl_id'] for c in candidates]
    )
    fallback_pool = [
        {
            'fpl_id':           pl.fpl_id,
            'web_name':         pl.web_name,
            'team_name':        pl.team.name if pl.team else '',
            'team_short':       pl.team.short_name if pl.team else '',
            'team_id':          pl.team_id or 0,
            'position':         pl.position,
            'position_name':    pl.get_position_display(),
            'price':            pl.price,
            'predicted_points': 0.0,
            'total_points':     pl.total_points,
            'form':             float(pl.form or 0),
            'status':           pl.status,
            'photo_code':       pl.code,
            'dream_team_count': 0,
        }
        for pl in _all_players
    ]

    xi, bench = _build_squad(candidates, budget, fallback_pool=fallback_pool)
    if not xi:
        return {'error': 'Not enough players available within budget.'}

    squad = xi + bench

    # Captain = highest captain_score among XI (optimises for upside/ceiling)
    # VC     = second highest captain_score
    from predictions.ml_loader import captain_score as _cap_score
    xi_players = Player.objects.filter(fpl_id__in=[p['fpl_id'] for p in xi])
    cap_scores  = {pl.fpl_id: _cap_score(pl) for pl in xi_players}
    xi_by_cap   = sorted(xi, key=lambda p: cap_scores.get(p['fpl_id'], 0), reverse=True)
    captain_id  = xi_by_cap[0]['fpl_id'] if xi_by_cap else -1
    vc_id       = xi_by_cap[1]['fpl_id'] if len(xi_by_cap) > 1 else -1

    total_cost   = round(sum(p['price'] for p in squad), 1)
    xi_pred_pts  = round(sum(
        p['predicted_points'] * (2 if p['fpl_id'] == captain_id else 1) for p in xi
    ), 2)

    xi_out    = [_to_pick(p, True,  None, captain_id, vc_id, fixtures, fdr_map) for p in xi]
    bench_out = [_to_pick(p, False, i+1, captain_id, vc_id, fixtures, fdr_map) for i, p in enumerate(bench)]

    n_def = sum(1 for p in xi if p['position'] == 2)
    n_mid = sum(1 for p in xi if p['position'] == 3)
    n_fwd = sum(1 for p in xi if p['position'] == 4)
    formation = f"{n_def}-{n_mid}-{n_fwd}"

    return {
        'gameweek':            gw.name if gw else 'N/A',
        'gameweek_id':         gw.fpl_id if gw else None,
        'budget':              budget,
        'total_cost':          total_cost,
        'remaining_budget':    round(budget - total_cost, 1),
        'xi_predicted_pts':    xi_pred_pts,
        'formation':           formation,
        'captain':             xi_by_cap[0]['web_name']    if xi_by_cap else None,
        'captain_photo_code':  xi_by_cap[0].get('photo_code') if xi_by_cap else None,
        'captain_position':    {1:'GK',2:'DEF',3:'MID',4:'FWD'}.get(xi_by_cap[0].get('position'), 'MID') if xi_by_cap else 'MID',
        'vice_captain':        xi_by_cap[1]['web_name']    if len(xi_by_cap) > 1 else None,
        'vc_photo_code':       xi_by_cap[1].get('photo_code') if len(xi_by_cap) > 1 else None,
        'vc_position':         {1:'GK',2:'DEF',3:'MID',4:'FWD'}.get(xi_by_cap[1].get('position'), 'MID') if len(xi_by_cap) > 1 else 'MID',
        'xi':                  xi_out,
        'bench':               bench_out,
        'squad':               xi_out + bench_out,
    }


def _multi_window_form_scores(player_ids: list[int], before_gw_id: int) -> dict[int, float]:
    """
    Multi-window recency scores for historical GW reconstruction.
    Fetches the last 5 GW actual points before before_gw_id per player,
    then computes: 45% × last-1-game + 35% × last-3-game-avg + 20% × last-5-game-avg.

    This is better than a simple 5-game equal-weight average because:
    - A player on a 3-game hot streak (e.g., 8,7,9 after 2,1,3) is rewarded more
    - A player whose only big game was 5 GWs ago is naturally discounted
    """
    from fpl.models import PlayerGameweekStats
    from collections import defaultdict

    prev_stats = (PlayerGameweekStats.objects
                  .filter(player_id__in=player_ids,
                          gameweek__fpl_id__lt=before_gw_id)
                  .order_by('player_id', '-gameweek__fpl_id')
                  .values('player_id', 'total_points'))

    grouped: dict[int, list[int]] = defaultdict(list)
    for s in prev_stats:
        if len(grouped[s['player_id']]) < 5:
            grouped[s['player_id']].append(s['total_points'])

    result = {}
    for pid, pts in grouped.items():
        w1 = float(pts[0])
        w3 = sum(pts[:3]) / min(len(pts), 3)
        w5 = sum(pts[:5]) / min(len(pts), 5)
        result[pid] = round(w1 * 0.25 + w3 * 0.35 + w5 * 0.40, 2)
    return result


def _rolling_form_scores(player_ids: list[int], before_gw_id: int, n: int = 5) -> dict[int, float]:
    """
    Gentle rolling average of actual points from the N GWs before before_gw_id.
    Uses equal weights to avoid overweighting a single big game.
    Returns {player_id: avg_pts_over_window}.
    """
    from fpl.models import PlayerGameweekStats
    from collections import defaultdict

    prev_stats = (PlayerGameweekStats.objects
                  .filter(player_id__in=player_ids,
                          gameweek__fpl_id__lt=before_gw_id,
                          gameweek__fpl_id__gte=before_gw_id - n)
                  .order_by('player_id', '-gameweek__fpl_id')
                  .values('player_id', 'total_points'))

    grouped: dict[int, list[int]] = defaultdict(list)
    for s in prev_stats:
        grouped[s['player_id']].append(s['total_points'])

    # Simple average over the window (equal weights avoid recency inflation)
    return {pid: round(sum(pts) / len(pts), 2) for pid, pts in grouped.items()}


def _season_avg_scores(player_ids: list[int], before_gw_id: int) -> dict[int, float]:
    """
    Compute each player's average points per GW across the whole season
    UP TO (not including) before_gw_id — no future data leakage.
    Divides cumulative points by total finished GWs before the target GW,
    so players who miss games are naturally penalised.
    Returns {player_id: season_avg}.
    """
    from fpl.models import PlayerGameweekStats, Gameweek
    from django.db.models import Sum

    gws_before = Gameweek.objects.filter(fpl_id__lt=before_gw_id, finished=True).count()
    if gws_before == 0:
        return {}

    totals = (PlayerGameweekStats.objects
              .filter(player_id__in=player_ids, gameweek__fpl_id__lt=before_gw_id)
              .values('player_id')
              .annotate(cum_pts=Sum('total_points')))

    return {row['player_id']: round(row['cum_pts'] / gws_before, 2) for row in totals}


def build_past_best_team(gw_fpl_id: int, captain_fpl_id: int | None = None) -> dict:
    """
    Reconstruct the best team for a past GW.

    Predicted points = blend of:
      1. Stored Prediction records for that GW (if run_predictions was run live)
      2. 40% rolling window average (last 5 GWs) + 60% season average up to that GW
         — the season average anchors predictions to realistic per-GW output and
           penalises players who miss games; the rolling window captures form.

    Actual points come from PlayerGameweekStats for that GW.
    """
    from fpl.models import Gameweek, PlayerGameweekStats
    from predictions.models import Prediction

    try:
        gw = Gameweek.objects.get(fpl_id=gw_fpl_id)
    except Gameweek.DoesNotExist:
        return {'error': f'GW {gw_fpl_id} not found'}

    from fpl.models import Team as _Team
    _team_name_to_short = {t.name: t.short_name for t in _Team.objects.all()}

    stats_qs = (PlayerGameweekStats.objects
                .filter(gameweek=gw)
                .select_related('player__team')
                .filter(player__now_cost__gt=0))

    if not stats_qs.exists():
        return {'error': f'No GW stats synced for GW {gw_fpl_id}. Run sync_fpl --players.'}

    stats_list  = list(stats_qs)
    player_ids  = [s.player_id for s in stats_list]

    # 1. Stored predictions (highest fidelity — use if available)
    stored_preds: dict[int, float] = {
        p.player_id: float(p.predicted_points)
        for p in Prediction.objects.filter(gameweek=gw, player_id__in=player_ids)
    }

    # 2. For players without stored predictions: blend multi-window form + season avg
    missing_ids  = [pid for pid in player_ids if pid not in stored_preds]
    rolling      = _multi_window_form_scores(missing_ids, gw_fpl_id) if missing_ids else {}
    season_avgs  = _season_avg_scores(missing_ids, gw_fpl_id)        if missing_ids else {}

    candidates = []
    for s in stats_list:
        pid = s.player_id
        if pid in stored_preds:
            pred_pts = stored_preds[pid]
        else:
            r = rolling.get(pid)
            a = season_avgs.get(pid, 2.0)
            if r is not None:
                # 40% multi-window form, 60% season average
                # Season avg anchors predictions to realistic per-GW output;
                # multi-window form captures genuine trends without chasing spikes
                pred_pts = round(r * 0.40 + a * 0.60, 2)
            else:
                pred_pts = a  # no form window data → use season avg alone

        # Use team_at_gw for historical accuracy (mid-season transfers)
        hist_team_short = (
            _team_name_to_short.get(s.team_at_gw)
            if s.team_at_gw else None
        ) or (s.player.team.short_name if s.player.team else '')
        hist_team_name = s.team_at_gw or (s.player.team.name if s.player.team else '')

        candidates.append({
            'fpl_id':             s.player.fpl_id,
            'web_name':           s.player.web_name,
            'team_name':          hist_team_name,
            'team_short':         hist_team_short,
            'team_at_gw':         s.team_at_gw or '',
            'team_id':            s.player.team_id or 0,
            'position':           s.player.position,
            'position_name':      s.player.get_position_display(),
            'price':              s.value / 10,
            'predicted_points':   pred_pts,
            'actual_points':      s.total_points,
            'total_points':       s.player.total_points,
            'form':               float(s.player.form or 0),
            'status':             s.player.status,
            'photo_code':         s.player.code,
            'dream_team_count':   s.player.dream_team_count or 0,
        })

    candidates.sort(key=lambda x: x['predicted_points'], reverse=True)

    xi, bench = _build_squad(candidates, 100.0)
    if not xi:
        return {'error': 'Could not build team'}

    fixtures = _get_fixtures(gw)
    fdr_map  = _get_fdr_map(gw)

    # Captain = 3-factor score: adjusted_pts×2 + dream_team_bonus
    # Uses same logic as build_best_team / manager optimizer
    def _past_cap_score(p):
        fdr      = fdr_map.get(p['team_id'], 3)
        adj_pts  = p['predicted_points'] * _FDR_CAP_MULT.get(fdr, 1.0)
        dt_bonus = p.get('dream_team_count', 0) * 0.5
        return adj_pts * 2 + dt_bonus

    xi_by_cap  = sorted(xi, key=_past_cap_score, reverse=True)
    # Use override captain_fpl_id when provided (e.g. from simulation cal_log)
    # so pitch view matches the GW History table captain exactly.
    if captain_fpl_id and any(p['fpl_id'] == captain_fpl_id for p in xi):
        captain_id = captain_fpl_id
        # VC = highest _past_cap_score that isn't the captain
        vc_id = next((p['fpl_id'] for p in xi_by_cap if p['fpl_id'] != captain_id), -1)
    else:
        captain_id = xi_by_cap[0]['fpl_id'] if xi_by_cap else -1
        vc_id      = xi_by_cap[1]['fpl_id'] if len(xi_by_cap) > 1 else -1

    def _pick(p, is_starter, bench_order):
        fdr = fdr_map.get(p['team_id'], 3)
        return {
            **p,
            'fixture':               fixtures.get(p['team_id'], ''),
            'fixture_difficulty':    fdr,
            'adjusted_points':       round(p['predicted_points'] * _FDR_CAP_MULT.get(fdr, 1.0), 2),
            'captain_appearances':   p.get('dream_team_count', 0),
            'dream_team_appearances': p.get('dream_team_count', 0),
            'is_captain':            p['fpl_id'] == captain_id,
            'is_vice_captain':       p['fpl_id'] == vc_id,
            'is_starter':            is_starter,
            'bench_order':           bench_order,
        }

    xi_out    = [_pick(p, True, None) for p in xi]
    bench_out = [_pick(p, False, i+1) for i, p in enumerate(bench)]

    # Captain's points are doubled — apply to both predicted and actual
    pred_xi_pts = round(sum(
        p['predicted_points'] * (2 if p['fpl_id'] == captain_id else 1)
        for p in xi
    ), 1)
    actual_xi_pts = round(sum(
        p.get('actual_points', 0) * (2 if p['fpl_id'] == captain_id else 1)
        for p in xi
    ), 1)

    n_def = sum(1 for p in xi if p['position'] == 2)
    n_mid = sum(1 for p in xi if p['position'] == 3)
    n_fwd = sum(1 for p in xi if p['position'] == 4)

    return {
        'gameweek':        gw.name,
        'gameweek_id':     gw.fpl_id,
        'formation':       f"{n_def}-{n_mid}-{n_fwd}",
        'predicted_pts':   pred_xi_pts,
        'actual_pts':      actual_xi_pts,
        'captain':         xi_by_cap[0]['web_name'] if xi_by_cap else None,
        'xi':              xi_out,
        'bench':           bench_out,
        'has_actual_data': True,
    }


# ─── Learning simulation ──────────────────────────────────────────────────────

def simulate_learning_progression(
    start_gw: int = 1,
    end_gw: int | None = None,
    reset: bool = True,
    cal_multipliers: dict[str, float] | None = None,
) -> list[dict]:
    """
    Simulate the adaptive scorer learning week-by-week from GW start_gw to end_gw.

    For each GW:
      1. Score all players using ONLY data available before that GW + current weights
      2. Build the best £100m team using those scores
      3. Reveal actual GW points and compute prediction error
      4. calibrate_after_gw() adjusts weights from those errors
      5. Updated weights are used for the next GW

    This demonstrates that the model learns from its mistakes — later GWs should
    show a smaller predicted-vs-actual gap than earlier GWs.

    If reset=True: resets weights to factory defaults before starting (clean test).
    If reset=False: continues from the currently saved weights.

    Returns a list of per-GW dicts:
      {gw, predicted_pts, actual_pts, diff, mae, captain, formation,
       weights_snapshot, calibration_summary}
    """
    from fpl.models import Gameweek, PlayerGameweekStats
    from predictions.scorer_weights import (
        score_all_players_before_gw, calibrate_after_gw,
        reset_weights, load_weights, save_weights, DEFAULT_WEIGHTS,
    )

    if reset:
        weights = reset_weights()
    else:
        weights = load_weights()

    # Determine GW range
    finished_gws = list(
        Gameweek.objects.filter(finished=True)
        .order_by('fpl_id')
        .values_list('fpl_id', flat=True)
    )
    if not finished_gws:
        return []

    if end_gw is None:
        end_gw = finished_gws[-1]

    target_gws = [g for g in finished_gws if start_gw <= g <= end_gw]
    if not target_gws:
        return []

    # Fetch dream_team_count once — used in captain utility inside the loop
    from fpl.models import Player as _Player
    _dt_map = {p.fpl_id: (p.dream_team_count or 0)
               for p in _Player.objects.only('fpl_id', 'dream_team_count')}

    results = []

    for gw_id in target_gws:
        # ── 1. Score players with current weights (data before this GW) ──────
        scored_map = score_all_players_before_gw(gw_id, weights, cal_multipliers)

        # Save per-player predicted_points to PlayerGameweekStats for this GW
        try:
            from fpl.models import PlayerGameweekStats as _PGWS
            stats_this_gw = list(
                _PGWS.objects
                .filter(gameweek__fpl_id=gw_id)
                .select_related('player')
            )
            for stat in stats_this_gw:
                entry = scored_map.get(stat.player.fpl_id)
                if entry is not None:
                    stat.predicted_points = entry['score']
            if stats_this_gw:
                _PGWS.objects.bulk_update(stats_this_gw, ['predicted_points'], batch_size=200)
        except Exception:
            pass

        # ── 2. Build best team ────────────────────────────────────────────────
        # Convert scored_map to candidates list for _build_squad
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
        candidates.sort(key=lambda x: x['predicted_points'], reverse=True)

        # NEW FIX 4: DEF clean-sheet correlation penalty.
        # Test result: avg|diff| −0.04 vs baseline (bad_GWs unchanged).
        # If 3+ DEF from the same team are in the candidate pool, apply ×0.92 to the
        # 3rd+ DEF to discourage concentration risk — when one team fails a CS, all
        # same-team DEF lose ~6pts simultaneously, creating correlated downside.
        _def_team_count: dict[int, int] = {}
        for c in [x for x in candidates if x['position'] == 2]:
            tid = c['team_id']
            _def_team_count[tid] = _def_team_count.get(tid, 0) + 1
            if _def_team_count[tid] >= 3:
                c['predicted_points'] = round(c['predicted_points'] * 0.92, 3)

        xi, bench = _build_squad(candidates, 100.0)
        if not xi:
            results.append({'gw': gw_id, 'error': 'Could not build squad'})
            # Still calibrate even if squad failed
            weights, cal = calibrate_after_gw(gw_id, weights, scored_map)
            save_weights(weights, gw_id, cal)
            continue

        # FIX 4: FDR-adjusted captain selection
        # Apply fixture difficulty as a multiplier on captain utility score
        # Lower FDR (easier fixture) boosts captaincy value
        from fpl.models import Fixture as _Fixture, Gameweek as _Gw
        fdr_map: dict[int, int] = {}
        try:
            _gw_obj = _Gw.objects.get(fpl_id=gw_id)
            for f in _Fixture.objects.filter(gameweek=_gw_obj).select_related('team_h','team_a'):
                if f.team_h_id and f.team_h_difficulty:
                    fdr_map[f.team_h_id] = f.team_h_difficulty
                if f.team_a_id and f.team_a_difficulty:
                    fdr_map[f.team_a_id] = f.team_a_difficulty
        except Exception:
            pass
        FDR_MULT = {1: 1.15, 2: 1.08, 3: 1.0, 4: 0.88, 5: 0.75}

        # FIX 6: Captain blank-rate penalty
        # Compute each XI player's historical blank rate (actual_pts <= 2 when played)
        # before this GW. High blank-rate players are discounted as captain picks.
        xi_fpl_ids = [p['fpl_id'] for p in xi]
        blank_rates: dict[int, float] = {}
        # NEW FIX 2: consecutive blank streak per player (last 3 GWs most-recent-first).
        # Test result: avg|diff| −0.03 vs baseline (H_cap: 30 → 27 GWs).
        # If a player blanked 2+ of the last 3 GWs, apply extra ×0.70 captain penalty.
        consec_blanks: dict[int, int] = {}
        try:
            from django.db.models import Count, Q
            for pid in xi_fpl_ids:
                stats_before = PlayerGameweekStats.objects.filter(
                    player__fpl_id=pid,
                    gameweek__fpl_id__lt=gw_id,
                    minutes__gt=0,
                ).order_by('-gameweek__fpl_id')
                total_apps = stats_before.count()
                blanks = stats_before.filter(total_points__lte=2).count()
                blank_rates[pid] = blanks / total_apps if total_apps >= 3 else 0.25
                # Count consecutive blanks from most recent GW backward
                cb = 0
                for s in stats_before[:3]:
                    if s.total_points <= 2:
                        cb += 1
                    else:
                        break
                consec_blanks[pid] = cb
        except Exception:
            pass

        def _cap_util(p):
            fdr  = fdr_map.get(p['team_id'], 3)
            br   = blank_rates.get(p['fpl_id'], 0.25)
            dt   = _dt_map.get(p['fpl_id'], 0)
            # Geometric blank penalty: (1 - blank_rate)^0.6
            # This is stronger than the linear (1 - 0.5*br) formula:
            #   br=0.10 → 0.94 (minimal penalty for reliable players)
            #   br=0.30 → 0.79 (noticeable penalty for moderate blankers)
            #   br=0.50 → 0.65 (strong penalty for coin-flip players like Haaland)
            # Consistent ~5.5pt player at 20% br: 5.5 * 0.83 = 4.57
            # Volatile ~8pt player at 48% br:     8.0 * 0.71 = 5.68 → still picks volatile
            # But at 55% br: 8 * 0.64 = 5.12 vs consistent 5.8 * 0.83 = 4.81 → volatile wins
            # Effect: starts diversifying when Haaland's blank rate climbs to 50%+
            blank_penalty = (1.0 - br) ** 0.6
            # NEW FIX 2: Extra ×0.70 if player blanked 2+ of last 3 GWs.
            # Test result: avg|diff| −0.03 vs baseline, reduces Haaland captaincy 30→27 GWs.
            if consec_blanks.get(p['fpl_id'], 0) >= 2:
                blank_penalty *= 0.70
            adj_pts = p['predicted_points'] * FDR_MULT.get(fdr, 1.0) * blank_penalty
            # Dream team bonus matches build_past_best_team / build_best_team formula
            return adj_pts * 2 + dt * 0.5

        xi_sorted  = sorted(xi, key=_cap_util, reverse=True)
        captain_id = xi_sorted[0]['fpl_id']
        vc_id      = xi_sorted[1]['fpl_id'] if len(xi_sorted) > 1 else -1

        pred_xi_pts = round(sum(
            p['predicted_points'] * (2 if p['fpl_id'] == captain_id else 1)
            for p in xi
        ), 1)

        # raw_pred_xi_pts = XI pts BEFORE position-specific cal_multipliers were applied.
        # Stored alongside pred_xi_pts so compute_calibration_multipliers() always
        # reads the uncalibrated values — prevents double-calibration on re-runs.
        if cal_multipliers:
            _pos_name_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
            raw_pred_xi_pts = round(sum(
                (p['predicted_points'] / cal_multipliers.get(
                    _pos_name_map.get(p['position'], 'MID'), 1.0))
                * (2 if p['fpl_id'] == captain_id else 1)
                for p in xi
            ), 1)
        else:
            raw_pred_xi_pts = pred_xi_pts

        # ── 3. Fetch actual points for this GW ────────────────────────────────
        actuals = {
            s.player.fpl_id: s.total_points
            for s in PlayerGameweekStats.objects
                        .filter(gameweek__fpl_id=gw_id)
                        .select_related('player')
        }
        actual_xi_pts = round(sum(
            actuals.get(p['fpl_id'], 0) * (2 if p['fpl_id'] == captain_id else 1)
            for p in xi
        ), 1)

        # Build hindsight "perfect XI" — best possible XI using actual pts as score
        # This is the theoretical ceiling: what a perfect model could have achieved.
        _perfect_cands = [
            {
                'fpl_id':           v['fpl_id'],
                'web_name':         v['web_name'],
                'team_name':        '',
                'team_short':       v['team_short'],
                'team_id':          v['team_id'],
                'position':         v['position'],
                'position_name':    {1:'GK',2:'DEF',3:'MID',4:'FWD'}.get(v['position'],''),
                'price':            v['price'],
                'predicted_points': float(actuals.get(v['fpl_id'], 0)),
                'total_points':     0,
                'form':             0.0,
                'status':           v['status'],
                'photo_code':       None,
            }
            for v in scored_map.values()
            if v['status'] in ('a', 'd') and v['price'] > 0
        ]
        _perfect_cands.sort(key=lambda x: x['predicted_points'], reverse=True)
        _perfect_xi, _ = _build_squad(_perfect_cands, 100.0)
        if _perfect_xi:
            _perfect_cap_id = max(_perfect_xi, key=lambda p: actuals.get(p['fpl_id'], 0))['fpl_id']
            perfect_pts = round(sum(
                actuals.get(p['fpl_id'], 0) * (2 if p['fpl_id'] == _perfect_cap_id else 1)
                for p in _perfect_xi
            ), 1)
        else:
            perfect_pts = None

        # Per-player MAE for this GW
        player_errors = [
            abs(actuals.get(p['fpl_id'], 0) - p['predicted_points'])
            for p in xi
            if p['fpl_id'] in actuals
        ]
        mae = round(sum(player_errors) / len(player_errors), 3) if player_errors else None

        n_def = sum(1 for p in xi if p['position'] == 2)
        n_mid = sum(1 for p in xi if p['position'] == 3)
        n_fwd = sum(1 for p in xi if p['position'] == 4)

        # ── 4. Calibrate weights from this GW's errors ────────────────────────
        weights, cal_summary = calibrate_after_gw(gw_id, weights, scored_map)
        # Persist team summary alongside calibration data for the history endpoint
        cal_summary['predicted_pts']     = pred_xi_pts
        cal_summary['raw_predicted_pts'] = raw_pred_xi_pts
        cal_summary['actual_pts']        = actual_xi_pts
        cal_summary['diff']          = round(actual_xi_pts - pred_xi_pts, 1)
        cal_summary['perfect_pts']   = perfect_pts
        cal_summary['model_gap']     = round(perfect_pts - pred_xi_pts, 1) if perfect_pts is not None else None
        cal_summary['squad_gap']     = round(perfect_pts - actual_xi_pts, 1) if perfect_pts is not None else None
        cal_summary['captain']        = xi_sorted[0]['web_name'] if xi_sorted else None
        cal_summary['captain_fpl_id'] = captain_id  # store so build_past_best_team can use same captain
        cal_summary['formation']      = f"{n_def}-{n_mid}-{n_fwd}"
        save_weights(weights, gw_id, cal_summary)

        results.append({
            'gw':               gw_id,
            'predicted_pts':    pred_xi_pts,
            'actual_pts':       actual_xi_pts,
            'diff':             round(actual_xi_pts - pred_xi_pts, 1),
            'perfect_pts':      perfect_pts,
            'model_gap':        round(perfect_pts - pred_xi_pts, 1) if perfect_pts is not None else None,
            'squad_gap':        round(perfect_pts - actual_xi_pts, 1) if perfect_pts is not None else None,
            'mae':              mae,
            'captain':          xi_sorted[0]['web_name'] if xi_sorted else None,
            'formation':        f"{n_def}-{n_mid}-{n_fwd}",
            'weights_snapshot': {k: round(v, 4) for k, v in weights.items()},
            'calibration':      cal_summary,
        })

    return results
