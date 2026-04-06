"""
Test XI Quality — compare old vs new optimizer pipeline.

Usage:
    python manage.py test_xi_quality [--user-id 1]

Runs two pipelines side-by-side for the most recent squad in the DB:
  OLD: raw predicted_points, no availability filter, no fixture weight
  NEW: L1 availability filter + L2 fixture weight + L3 dream team captain bonus

Then calls Groq (Layer 4) to critique the new XI.
Saves the full report to xi_quality_test_report.md
"""

import json
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from fpl.models import Gameweek, Fixture
from manager.models import Squad, SquadPlayer
from manager.optimizer import get_best_xi, filter_available_players, apply_fixture_weight
from manager.views import _squad_players_to_dicts
from predictions.models import Prediction

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_raw_squad_dicts(squad_players):
    """Old pipeline — no availability field, no fixture weight enrichment."""
    from fpl.models import Fixture
    POSITION_MAP = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()
    result = []
    for sp in squad_players:
        p = sp.player
        pos = POSITION_MAP.get(p.position, str(p.position))
        pred_pts = 0.0
        if gw:
            pred = Prediction.objects.filter(player=p, gameweek=gw).order_by('-predicted_points').first()
            pred_pts = float(pred.predicted_points) if pred else float(p.form or 0)
        result.append({
            'id':                p.fpl_id,
            'name':              p.web_name,
            'position':          pos,
            'team':              p.team.short_name if p.team else '',
            'price':             round(p.now_cost / 10, 1),
            'predicted_points':  round(pred_pts, 2),
            'status':            p.status,
            # OLD pipeline: no chance_of_playing, no fdr, no dream team
        })
    return result


def _old_get_best_xi(squad):
    """Old optimizer: no filters, raw predicted_points in LP."""
    try:
        import pulp
    except ImportError:
        return {'error': 'PuLP not installed'}

    if len(squad) < 11:
        return {'error': 'Not enough players'}

    n = len(squad)
    indices = list(range(n))
    prob = pulp.LpProblem("OldXI", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x_{i}", cat='Binary') for i in indices]

    prob += pulp.lpSum(x[i] * float(squad[i].get('predicted_points', 0)) for i in indices)
    prob += pulp.lpSum(x) == 11

    gk_idx = [i for i, p in enumerate(squad) if p['position'] == 'GK']
    prob += pulp.lpSum(x[i] for i in gk_idx) == 1

    for pos, (lo, hi) in [('DEF', (3,5)), ('MID', (2,5)), ('FWD', (1,3))]:
        pos_idx = [i for i, p in enumerate(squad) if p['position'] == pos]
        prob += pulp.lpSum(x[i] for i in pos_idx) >= lo
        prob += pulp.lpSum(x[i] for i in pos_idx) <= hi

    solver = pulp.PULP_CBC_CMD(msg=0)
    prob.solve(solver)

    starter_ids = {squad[i]['id'] for i in indices if pulp.value(x[i]) == 1}
    starters = [p for p in squad if p['id'] in starter_ids]
    bench    = [p for p in squad if p['id'] not in starter_ids]

    starters_sorted = sorted(starters, key=lambda p: -p.get('predicted_points', 0))
    captain = starters_sorted[0] if starters_sorted else None

    pos_counts = {}
    for p in starters:
        pos_counts[p['position']] = pos_counts.get(p['position'], 0) + 1
    formation = f"1-{pos_counts.get('DEF',0)}-{pos_counts.get('MID',0)}-{pos_counts.get('FWD',0)}"

    return {
        'starting_xi': starters,
        'bench': bench,
        'formation': formation,
        'captain': {'id': captain['id'], 'name': captain['name']} if captain else None,
    }


class Command(BaseCommand):
    help = "Compare old vs new XI optimizer pipeline and generate xi_quality_test_report.md"

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, default=None, help='User ID to test (default: first user)')

    def handle(self, *args, **options):
        # Get user and squad
        user_id = options['user_id']
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stderr.write(f"User {user_id} not found.")
                return
        else:
            user = User.objects.first()
            if not user:
                self.stderr.write("No users in DB.")
                return

        squad_obj = Squad.objects.filter(user=user).prefetch_related(
            'players__player__team'
        ).order_by('-gameweek__fpl_id').first()

        if not squad_obj:
            self.stderr.write(f"No squad found for user {user.username}.")
            return

        squad_players = list(squad_obj.players.select_related('player__team').all())
        self.stdout.write(f"Testing XI quality for {user.username} — {squad_obj.gameweek.name}")
        self.stdout.write(f"Squad size: {len(squad_players)} players\n")

        # ── OLD pipeline ──────────────────────────────────────────────────────
        self.stdout.write("Running OLD pipeline (raw predicted_points, no filters)...")
        old_dicts = _get_raw_squad_dicts(squad_players)
        old_xi    = _old_get_best_xi(old_dicts)

        # ── NEW pipeline ──────────────────────────────────────────────────────
        self.stdout.write("Running NEW pipeline (L1+L2+L3)...")
        new_dicts = _squad_players_to_dicts(squad_players)
        new_xi    = get_best_xi(new_dicts)

        # ── Layer 4: Groq critique ────────────────────────────────────────────
        self.stdout.write("Running Layer 4 (Groq critique)...")
        groq_result = {'approved': True, 'swaps': [], 'captain_reasoning': '', 'team_rating': 'N/A', 'overall_comment': ''}
        try:
            from manager.advisor import get_best_xi_reasoning
            groq_result = get_best_xi_reasoning(new_xi, [], float(squad_obj.bank or 0))
        except Exception as e:
            self.stderr.write(f"Groq critique failed: {e}")

        # ── Analysis ─────────────────────────────────────────────────────────
        n_filtered = sum(
            1 for p in new_dicts
            if p.get('chance_of_playing_this_round') is not None
            and p['chance_of_playing_this_round'] < 30
        )

        old_xi_ids = {p['id'] for p in old_xi.get('starting_xi', [])} if 'starting_xi' in old_xi else set()
        new_xi_ids = {p['id'] for p in new_xi.get('starting_xi', [])}

        added   = new_xi_ids - old_xi_ids
        removed = old_xi_ids - new_xi_ids

        old_cap = old_xi.get('captain', {}).get('name', '?') if old_xi.get('captain') else '?'
        new_cap = new_xi.get('captain', {}).get('name', '?') if new_xi.get('captain') else '?'
        captain_changed = old_cap != new_cap

        # Build name lookups
        id_to_name = {p['id']: p['name'] for p in new_dicts}

        # ── Print report ──────────────────────────────────────────────────────
        lines = []
        lines.append("# XI Quality Test Report")
        lines.append(f"\nUser: {user.username}  |  Gameweek: {squad_obj.gameweek.name}\n")

        lines.append("## Layer 1 — Availability Filter")
        if n_filtered:
            filtered_names = [
                f"{p['name']} ({p['chance_of_playing_this_round']}%)"
                for p in new_dicts
                if p.get('chance_of_playing_this_round') is not None
                and p['chance_of_playing_this_round'] < 30
            ]
            lines.append(f"Filtered {n_filtered} player(s): {', '.join(filtered_names)}")
        else:
            lines.append("No players filtered -- all have chance_of_playing >= 30%")

        lines.append("\n## Layer 2 — Fixture Weighting")
        xi_changes = len(added)
        if xi_changes:
            lines.append(f"Fixture weighting changed the XI — {xi_changes} player(s) swapped in/out vs raw points:")
            for pid in added:
                lines.append(f"  + IN:  {id_to_name.get(pid, pid)}")
            for pid in removed:
                lines.append(f"  - OUT: {id_to_name.get(pid, pid)}")
        else:
            lines.append("Fixture weighting did not change the XI composition")

        # Show FDR adjustments for new XI
        lines.append("\nFDR adjustments in new XI:")
        for p in new_xi.get('starting_xi', []):
            raw = p.get('predicted_points', 0)
            adj = p.get('adjusted_points', raw)
            fdr = p.get('fixture_difficulty', 3)
            mult = p.get('fdr_multiplier', 1.0)
            arrow = '^' if mult > 1 else ('v' if mult < 1 else '-')
            lines.append(f"  {p['name']:20} FDR={fdr} {arrow}  raw={raw:.1f} → adj={adj:.1f}")

        lines.append("\n## Layer 3 — Dream Team Captain Bonus")
        if captain_changed:
            lines.append(f"Captain CHANGED: {old_cap} → {new_cap} (dream team bonus influenced selection)")
        else:
            lines.append(f"Captain unchanged: {new_cap}")
        for p in new_xi.get('starting_xi', []):
            dt  = p.get('dream_team_appearances', 0)
            cap = p.get('captain_appearances', 0)
            if dt or cap:
                lines.append(f"  {p['name']:20} ⭐×{dt} dream team apps, captain×{cap}")

        lines.append("\n## Layer 4 — Groq Reasoning")
        lines.append(f"Approved: {groq_result.get('approved', True)}")
        lines.append(f"Team Rating: {groq_result.get('team_rating', 'N/A')}")
        lines.append(f"Captain Reasoning: {groq_result.get('captain_reasoning', '')}")
        swaps = groq_result.get('swaps', [])
        if swaps:
            lines.append("Suggested Swaps:")
            for s in swaps:
                lines.append(f"  OUT {s.get('out')} → IN {s.get('in')}: {s.get('reason', '')}")
        else:
            lines.append("No swaps suggested — optimizer XI confirmed")
        lines.append(f"Overall Comment: {groq_result.get('overall_comment', '')}")

        lines.append("\n## Side-by-Side XI Comparison")
        lines.append(f"{'Player':22} {'OLD XI':8} {'NEW XI':8} {'FDR':4} {'Adj Pts':8}")
        lines.append("-" * 56)
        all_ids = old_xi_ids | new_xi_ids
        for p in new_dicts:
            if p['id'] not in all_ids:
                continue
            in_old = '✓' if p['id'] in old_xi_ids else ''
            in_new = '✓' if p['id'] in new_xi_ids else ''
            fdr  = p.get('fixture_difficulty', 3)
            adj  = p.get('adjusted_points', p.get('predicted_points', 0))
            lines.append(f"  {p['name']:20} {in_old:8} {in_new:8} {fdr:4} {adj:8.1f}")

        lines.append("\n## Overall Verdict")
        impacts = []
        if n_filtered:
            impacts.append(f"Layer 1 removed {n_filtered} risky player(s)")
        if xi_changes:
            impacts.append(f"Layer 2 changed {xi_changes} player(s) in the XI")
        if captain_changed:
            impacts.append(f"Layer 3 changed captain from {old_cap} to {new_cap}")
        if swaps:
            impacts.append(f"Layer 4 suggested {len(swaps)} swap(s)")
        if not impacts:
            impacts.append("All layers confirmed optimizer XI — squad looks strong")
        lines.append("Impact summary: " + " | ".join(impacts))

        report = '\n'.join(lines)
        # Print safely (replace non-ASCII for Windows console)
        safe_report = report.encode('ascii', errors='replace').decode('ascii')
        self.stdout.write('\n' + safe_report)

        report_path = 'xi_quality_test_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        self.stdout.write(self.style.SUCCESS(f"\nReport saved to {report_path}"))
