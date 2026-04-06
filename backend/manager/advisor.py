"""
FPL Manager Advisor
===================
Heuristic advisor (existing squad management) + Claude-powered transfer advice.

Claude function:
    get_transfer_advice(squad, predictions, budget_remaining, free_transfers) -> dict

Existing heuristic functions (used by other views):
    generate_transfer_suggestions(user) -> list[TransferSuggestion]
    generate_captain_suggestion(user)   -> CaptainSuggestion | None
    generate_chip_advice(user)          -> list[ChipAdvice]
"""

import json
import logging
from typing import Optional

from groq import Groq
from django.conf import settings

from fpl.models import Player, Gameweek, PlayerGameweekStats, Fixture
from predictions.models import Prediction, BestPickRecommendation
from .models import Squad, SquadPlayer, TransferSuggestion, CaptainSuggestion, ChipAdvice

logger = logging.getLogger(__name__)

POSITION_MAP = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

# ── FPL Rules encoded in system prompt ────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert Fantasy Premier League (FPL) analyst and advisor.

FPL RULES YOU MUST ENFORCE:
- Squad: exactly 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)
- Playing XI: exactly 11, valid formation requires min 1 GK, 3 DEF, 2 MID, 1 FWD
- Budget: total squad cost must not exceed £100m; check budget_remaining after transfer
- Max 3 players from the same club at all times
- Transfers: 1 free transfer per gameweek; each additional costs -4 points
- Chips available: Wildcard (unlimited transfers), Free Hit (temporary squad for 1 GW),
  Bench Boost (bench players score), Triple Captain (captain points x3)

TRANSFER EVALUATION CRITERIA (in priority order):
1. Predicted points for next gameweek (primary signal — from ML model)
2. Fixture difficulty rating (FDR 1=easy, 5=hard)
3. Current form and injury/doubt status
4. Ownership % — high ownership = template, low ownership = differential
5. Price and budget impact

RESPONSE FORMAT:
Return ONLY valid JSON with no markdown fences, no preamble, no commentary outside the JSON.
If no worthwhile transfer exists (gain < 1 predicted point), set transfer_out and transfer_in to null.
"""

_USER_TEMPLATE = """Current squad (15 players):
{squad_text}

Top replacement candidates (not in squad, filtered by position & budget):
{candidates_text}

Budget remaining in bank: £{budget_remaining}m
Free transfers available: {free_transfers}
Next gameweek: {gw_name}

Suggest the single best transfer (or no transfer if none is worth it).
Respond with ONLY this JSON:
{{
  "transfer_out": {{"id": <int>, "name": "<str>", "reason": "<str>"}},
  "transfer_in":  {{"id": <int>, "name": "<str>", "reason": "<str>"}},
  "budget_after": <float>,
  "risk_level": "<safe|differential|avoid>",
  "reasoning": "<one paragraph explaining the full decision>"
}}
If no transfer: set transfer_out and transfer_in to null, still provide reasoning."""


# ── Claude transfer advice ─────────────────────────────────────────────────────

def get_transfer_advice(
    squad: list[dict],
    predictions: list[dict],
    budget_remaining: float,
    free_transfers: int,
) -> dict:
    """
    Call Claude to recommend the best single transfer.

    Parameters
    ----------
    squad : list[dict]
        Each dict: {id, name, position, team, price, predicted_points,
                    ownership_pct, fixture_difficulty}
    predictions : list[dict]
        Top available players not in squad, same schema as squad dicts.
    budget_remaining : float
        Money in bank (£m).
    free_transfers : int
        Free transfers available this GW.

    Returns
    -------
    dict with keys: transfer_out, transfer_in, budget_after, risk_level, reasoning
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured in settings.")

    gw = _get_next_gw()
    gw_name = gw.name if gw else "Next Gameweek"

    def _fmt_player(p):
        status = p.get('status', 'a')
        status_str = '' if status == 'a' else f' [{status.upper()}]'
        return (
            f"  id={p['id']} {p['name']:20} {p['position']} {p['team']:5} "
            f"£{p['price']}m  pred={p.get('predicted_points', '?')}pts  "
            f"fdr={p.get('fixture_difficulty', '?')}  own={p.get('ownership_pct', '?')}%"
            f"{status_str}"
        )

    squad_text = '\n'.join(_fmt_player(p) for p in squad)
    candidates_text = '\n'.join(_fmt_player(p) for p in predictions) if predictions else '  (none available)'

    user_msg = _USER_TEMPLATE.format(
        squad_text=squad_text,
        candidates_text=candidates_text,
        budget_remaining=f"{budget_remaining:.1f}",
        free_transfers=free_transfers,
        gw_name=gw_name,
    )

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': _SYSTEM_PROMPT},
                {'role': 'user', 'content': user_msg},
            ],
            temperature=0.3,
        )
    except Exception as e:
        raise RuntimeError(f"Groq API error: {e}") from e

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if raw.startswith('```'):
        parts = raw.split('```')
        raw = parts[1].lstrip('json').strip() if len(parts) > 1 else raw

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\nRaw response:\n{raw}") from e

    required = {'transfer_out', 'transfer_in', 'budget_after', 'risk_level', 'reasoning'}
    missing = required - result.keys()
    if missing:
        raise ValueError(f"Claude response missing fields: {missing}")

    # Guard: if Groq suggests the same player in and out, nullify the transfer
    t_in  = result.get('transfer_in')
    t_out = result.get('transfer_out')
    if t_in and t_out and t_in.get('id') == t_out.get('id'):
        result['transfer_in']  = None
        result['transfer_out'] = None
        result['reasoning']    = "No valid transfer found this gameweek."

    return result


# ── Layer 4: Groq Best-XI reasoning ──────────────────────────────────────────

_XI_SYSTEM_PROMPT = """You are an expert Fantasy Premier League (FPL) manager with 10+ years experience.

You will receive a proposed Best XI selected by a mathematical optimizer that already incorporates:
- Fixture difficulty weighting (adjusted_points = predicted_points * FDR multiplier)
- Dream team historical data (captain_appearances shows how many times the player was the top-scoring captain)

Your job is to:
1. Identify any obvious mistakes (injured players, bad fixtures, 0-minute risks, over-reliance on one team)
2. Suggest up to 2 swaps ONLY if a clearly better option exists in the candidates list within the available budget
3. Write a decisive, committed captain_reasoning — one or two sentences explaining WHY the chosen captain is correct given their fixture and form
4. Rate the overall team quality: "strong" / "average" / "risky"
5. Evaluate whether the user should use any FPL chips THIS gameweek

CAPTAIN RULES (strictly follow these):
- The optimizer has already selected the captain using dream team data and fixture weighting — trust this decision
- Do NOT suggest switching back to a different captain unless that player has an injury concern or a clearly inferior fixture (FDR 4 or 5)
- Be decisive: commit fully to the captain chosen. Do NOT say "X is good but Y might also be worth considering"
- Write the captain_reasoning as if you fully endorse the choice, referencing their opponent or home/away advantage

SWAP RULES:
- Only suggest swaps for players listed in the candidates section
- Respect formation constraints (min 3 DEF, 2 MID, 1 FWD starting)
- Never suggest a swap that exceeds the budget
- If no compelling swap exists, set swaps to [] — do not invent swaps
- For each swap write a "reason" that is 2-3 sentences: why the player going out is being dropped AND why the replacement is the right choice (fixture, form, ownership, xG)

CHIP ADVICE RULES:
- bench_boost: Recommend if the bench predicted total > 18 pts OR there's a clear double gameweek bonus for bench players. Otherwise no.
- triple_captain: Recommend if the captain has FDR 1-2 AND adjusted points > 8, making a 3x return highly probable. Otherwise no.
- free_hit: Recommend if 4 or more starting XI players have FDR 4-5 this week, making a temporary full squad swap worthwhile. Otherwise no.
- wildcard: Recommend ONLY if the squad fundamentally needs rebuilding — 3 or more players injured/unavailable OR consistently underperforming (not just one bad gameweek). Never recommend wildcard for routine upgrades.
- For each chip: "recommended" true/false, "confidence" high/medium/low, "reasoning" one clear sentence with a specific reason referencing the squad data above.

Return ONLY valid JSON (no markdown, no preamble):
{
  "approved": true/false,
  "swaps": [{"out": "player name", "in": "player name", "reason": "2-3 sentences"}],
  "captain_reasoning": "one to two sentences — decisive, committed, fixture-specific",
  "team_rating": "strong|average|risky",
  "overall_comment": "one short paragraph",
  "chip_advice": {
    "bench_boost":     {"recommended": true/false, "confidence": "high|medium|low", "reasoning": "one sentence"},
    "triple_captain":  {"recommended": true/false, "confidence": "high|medium|low", "reasoning": "one sentence"},
    "free_hit":        {"recommended": true/false, "confidence": "high|medium|low", "reasoning": "one sentence"},
    "wildcard":        {"recommended": true/false, "confidence": "high|medium|low", "reasoning": "one sentence"}
  }
}"""

_XI_USER_TEMPLATE = """Proposed Best XI (optimizer output):
Formation: {formation}
Captain: {captain}

Starting XI:
{xi_text}

Bench (predicted pts shown — important for Bench Boost evaluation):
{bench_text}

Available candidates for swaps (not in squad, within budget):
{candidates_text}

Budget remaining: £{budget_remaining}m
Free transfers available: {free_transfers}
Next gameweek: {gw_name}

Bench total predicted points: {bench_total:.1f} pts

Critique this XI, suggest any swaps, and evaluate all 4 chips. Return JSON."""


def get_best_xi_reasoning(
    pulp_xi: dict,
    all_players: list[dict],
    budget_remaining: float,
    free_transfers: int = 1,
) -> dict:
    """
    Layer 4: ask Groq to critique the PuLP Best XI, suggest swaps, and advise on chips.

    Parameters
    ----------
    pulp_xi : dict
        Output of get_best_xi() — starting_xi, bench, formation, captain, vice_captain
    all_players : list[dict]
        All candidate players (not in squad) available for potential swaps
    budget_remaining : float
        Money in bank (£m)
    free_transfers : int
        Free transfers available this GW (default 1)

    Returns
    -------
    dict with keys: approved, swaps, captain_reasoning, team_rating, overall_comment, chip_advice
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        return {'error': 'GROQ_API_KEY not configured', 'approved': True, 'swaps': [],
                'captain_reasoning': '', 'team_rating': 'average', 'overall_comment': '',
                'chip_advice': {}}

    gw = _get_next_gw()
    gw_name = gw.name if gw else "Next Gameweek"

    def _fmt(p):
        chance = p.get('chance_of_playing', p.get('chance_of_playing_this_round'))
        chance_str = f" [{chance}% chance]" if chance is not None and chance < 100 else ""
        fdr = p.get('fixture_difficulty', 3)
        fdr_arrow = '↑' if fdr <= 2 else ('↓' if fdr >= 4 else '→')
        dt = p.get('dream_team_appearances', 0)
        dt_str = f" ⭐×{dt}" if dt else ""
        cap = p.get('captain_appearances', 0)
        cap_str = f" (C×{cap})" if cap else ""
        adj = p.get('adjusted_points', p.get('predicted_points', 0))
        return (
            f"  {p.get('name', p.get('web_name', '?')):20} {p.get('position','?')} "
            f"{p.get('team','?'):5} £{p.get('price', 0)}m  "
            f"adj={adj:.1f}pts FDR={fdr}{fdr_arrow}{chance_str}{dt_str}{cap_str}"
        )

    bench_players = pulp_xi.get('bench', [])
    bench_total   = sum(p.get('predicted_points', 0) for p in bench_players)

    xi_text      = '\n'.join(_fmt(p) for p in pulp_xi.get('starting_xi', []))
    bench_text   = '\n'.join(_fmt(p) for p in bench_players)
    # Limit candidates to top 20 by adjusted/predicted points
    sorted_cands = sorted(all_players, key=lambda p: -p.get('adjusted_points', p.get('predicted_points', 0)))
    cands_text   = '\n'.join(_fmt(p) for p in sorted_cands[:20]) if sorted_cands else '  (none)'

    user_msg = _XI_USER_TEMPLATE.format(
        formation=pulp_xi.get('formation', '?'),
        captain=pulp_xi.get('captain', {}).get('name', '?') if pulp_xi.get('captain') else '?',
        xi_text=xi_text,
        bench_text=bench_text,
        candidates_text=cands_text,
        budget_remaining=f"{budget_remaining:.1f}",
        free_transfers=free_transfers,
        gw_name=gw_name,
        bench_total=bench_total,
    )

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': _XI_SYSTEM_PROMPT},
                {'role': 'user',   'content': user_msg},
            ],
            temperature=0.2,
        )
    except Exception as e:
        logger.warning("Groq XI reasoning failed: %s", e)
        return {'approved': True, 'swaps': [], 'captain_reasoning': '',
                'team_rating': 'average', 'overall_comment': f'Reasoning unavailable: {e}'}

    raw = response.choices[0].message.content.strip()
    if raw.startswith('```'):
        parts = raw.split('```')
        raw = parts[1].lstrip('json').strip() if len(parts) > 1 else raw

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Groq XI reasoning returned invalid JSON: %s", raw[:200])
        return {'approved': True, 'swaps': [], 'captain_reasoning': '',
                'team_rating': 'average', 'overall_comment': raw[:500], 'chip_advice': {}}

    # Ensure required keys are present
    result.setdefault('approved', True)
    result.setdefault('swaps', [])
    result.setdefault('captain_reasoning', '')
    result.setdefault('team_rating', 'average')
    result.setdefault('overall_comment', '')
    result.setdefault('chip_advice', {})
    return result


# ── Helpers shared by heuristic functions ─────────────────────────────────────

def _get_next_gw() -> Optional[Gameweek]:
    return Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()


def _get_player_prediction(player: Player, gameweek: Gameweek) -> float:
    pred = Prediction.objects.filter(player=player, gameweek=gameweek).order_by('-predicted_points').first()
    return pred.predicted_points if pred else float(player.form or 0)


# ── Heuristic advisor (existing logic, kept for other views) ──────────────────

def generate_transfer_suggestions(user, max_suggestions: int = 5) -> list:
    gw = _get_next_gw()
    if not gw:
        return []

    try:
        squad = Squad.objects.get(user=user, gameweek=gw)
    except Squad.DoesNotExist:
        squad = Squad.objects.filter(user=user).first()
        if not squad:
            return []

    squad_players = SquadPlayer.objects.filter(squad=squad).select_related('player__team')
    current_player_ids = {sp.player.fpl_id for sp in squad_players}
    suggestions = []

    for sp in squad_players:
        player_out = sp.player
        pos = player_out.position
        sell_price = sp.selling_price / 10 if sp.selling_price else player_out.price
        budget = sell_price + squad.bank
        out_pred = _get_player_prediction(player_out, gw)

        candidates = (
            Player.objects
            .filter(position=pos, now_cost__lte=int(budget * 10), status='a')
            .exclude(fpl_id__in=current_player_ids)
            .select_related('team')
            .order_by('-total_points')[:50]
        )

        best_candidate = None
        best_gain = 0.5

        for candidate in candidates:
            in_pred = _get_player_prediction(candidate, gw)
            gain = in_pred - out_pred
            if gain > best_gain:
                best_gain = gain
                best_candidate = candidate

        if best_candidate:
            cost_impact = sell_price - (best_candidate.now_cost / 10)
            reason = _classify_transfer_reason(player_out, best_candidate, best_gain)
            suggestion = TransferSuggestion(
                user=user,
                gameweek=gw,
                player_out=player_out,
                player_in=best_candidate,
                points_gain=round(best_gain, 2),
                reason=reason,
                reason_detail=_build_reason_detail(player_out, best_candidate, best_gain, gw),
                cost_impact=round(cost_impact, 1),
            )
            suggestions.append(suggestion)

    suggestions.sort(key=lambda s: s.points_gain, reverse=True)

    # Deduplicate: same player_in should not appear twice (highest-gain entry wins)
    seen_in = set()
    unique: list = []
    for s in suggestions:
        pid = s.player_in.fpl_id
        if pid not in seen_in:
            seen_in.add(pid)
            unique.append(s)

    # Deduplicate: same player_out should not appear twice either
    seen_out = set()
    final: list = []
    for s in unique:
        pid = s.player_out.fpl_id
        if pid not in seen_out:
            seen_out.add(pid)
            final.append(s)

    suggestions = final[:max_suggestions]

    TransferSuggestion.objects.filter(user=user, gameweek=gw).delete()
    TransferSuggestion.objects.bulk_create(suggestions)
    return suggestions


def _classify_transfer_reason(player_out: Player, player_in: Player, gain: float) -> str:
    if player_out.status != 'a':
        return 'injury'
    if gain > 3:
        return 'prediction'
    if float(player_in.form or 0) > float(player_out.form or 0) + 2:
        return 'form'
    if float(player_in.selected_by_percent or 0) < 5:
        return 'differential'
    return 'fixture'


def _build_reason_detail(player_out, player_in, gain, gw) -> str:
    return (
        f"Swap {player_out.web_name} (£{player_out.price}m, form {player_out.form}) "
        f"for {player_in.web_name} (£{player_in.price}m, form {player_in.form}). "
        f"Predicted gain: +{gain:.1f} pts in GW{gw.fpl_id}."
    )


def generate_captain_suggestion(user) -> Optional[CaptainSuggestion]:
    gw = _get_next_gw()
    if not gw:
        return None

    squad = Squad.objects.filter(user=user).order_by('-gameweek__fpl_id').first()
    if not squad:
        return None

    starters = SquadPlayer.objects.filter(squad=squad, is_starter=True).select_related('player')
    if not starters:
        return None

    ranked = sorted(starters, key=lambda sp: _get_player_prediction(sp.player, gw), reverse=True)
    if len(ranked) < 2:
        return None

    captain = ranked[0].player
    vc = ranked[1].player
    captain_pred = _get_player_prediction(captain, gw)
    vc_pred = _get_player_prediction(vc, gw)

    differential = None
    for sp in ranked[2:]:
        p = sp.player
        if float(p.selected_by_percent or 100) < 10:
            differential = p
            break

    suggestion, _ = CaptainSuggestion.objects.update_or_create(
        user=user,
        gameweek=gw,
        defaults={
            'captain': captain,
            'vice_captain': vc,
            'captain_predicted': captain_pred,
            'vc_predicted': vc_pred,
            'differential_captain': differential,
        },
    )
    return suggestion


def generate_chip_advice(user) -> list:
    gw = _get_next_gw()
    if not gw:
        return []

    top_preds = BestPickRecommendation.objects.filter(
        gameweek=gw, rank_in_position__lte=3
    ).select_related('player')
    top_predicted_total = sum(r.predicted_points for r in top_preds)

    squad = Squad.objects.filter(user=user).order_by('-gameweek__fpl_id').first()
    bench_score = 0.0
    if squad:
        bench_players = SquadPlayer.objects.filter(squad=squad, is_starter=False).select_related('player')
        bench_total = sum(_get_player_prediction(sp.player, gw) for sp in bench_players)
        bench_score = min(bench_total / 20, 10)

    chips = [
        {
            'chip': 'benchboost',
            'recommended': bench_score > 6,
            'score': bench_score,
            'reason': f"Bench players predicted {bench_score:.1f}/10 value score.",
        },
        {
            'chip': 'triplecaptain',
            'recommended': top_predicted_total > 40,
            'score': min(top_predicted_total / 6, 10),
            'reason': f"Top GW predictions sum to {top_predicted_total:.1f} pts — strong TC week.",
        },
    ]

    advice_list = []
    for c in chips:
        advice, _ = ChipAdvice.objects.update_or_create(
            user=user, gameweek=gw, chip=c['chip'],
            defaults={
                'recommended': c['recommended'],
                'score': c['score'],
                'reason': c['reason'],
            },
        )
        advice_list.append(advice)

    return advice_list
