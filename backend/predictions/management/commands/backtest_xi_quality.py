"""
Backtest XI quality: model predicted XI vs perfect hindsight XI for every GW.

For each completed GW:
  1. Perfect XI  — best 11 players by actual points (ignoring formation/budget)
  2. Model XI    — best 11 players by stored predicted_points
  3. Diff        — players in perfect XI but not in model XI (the missed opportunities)

Aggregates across all GWs to find which players the model consistently underrates.

Usage:
  python manage.py backtest_xi_quality
  python manage.py backtest_xi_quality --start-gw 1 --end-gw 29
  python manage.py backtest_xi_quality --output backtest_xi_quality.json
"""
import json
from collections import defaultdict
from django.core.management.base import BaseCommand
from fpl.models import Gameweek, PlayerGameweekStats, Fixture


class Command(BaseCommand):
    help = 'Backtest model XI vs perfect hindsight XI across all finished GWs'

    def add_arguments(self, parser):
        parser.add_argument('--start-gw', type=int, default=1)
        parser.add_argument('--end-gw',   type=int, default=None)
        parser.add_argument('--output',   type=str, default='backtest_xi_quality.json')

    # ── Captain scoring helpers ────────────────────────────────────────────────

    @staticmethod
    def _get_fdr_map(gw):
        """Return {team_id: fdr} for the given gameweek."""
        fdr_map = {}
        try:
            for f in Fixture.objects.filter(gameweek=gw).select_related('team_h', 'team_a'):
                if f.team_h_id and f.team_h_difficulty:
                    fdr_map[f.team_h_id] = f.team_h_difficulty
                if f.team_a_id and f.team_a_difficulty:
                    fdr_map[f.team_a_id] = f.team_a_difficulty
        except Exception:
            pass
        return fdr_map

    @staticmethod
    def _blank_rate(player_id, before_gw_id):
        """Fraction of played GWs (before this GW) where player scored ≤2 pts."""
        stats = PlayerGameweekStats.objects.filter(
            player_id=player_id, gameweek__fpl_id__lt=before_gw_id, minutes__gt=0
        )
        total = stats.count()
        if total < 3:
            return 0.25
        blanks = stats.filter(total_points__lte=2).count()
        return blanks / total

    def _cap_score(self, stat, fdr_map, blank_rates):
        """
        Mirror of _cap_util in optimizer.py:
          adj_pts * 2  (FDR-weighted predicted_points)
        + blank_penalty (geometric)
        + dream_team_count * 0.5
        """
        FDR_MULT = {1: 1.15, 2: 1.08, 3: 1.0, 4: 0.88, 5: 0.75}
        fdr     = fdr_map.get(stat.player.team_id, 3)
        br      = blank_rates.get(stat.player_id, 0.25)
        dt      = stat.player.dream_team_count or 0
        pred    = float(stat.predicted_points or 0)
        adj     = pred * FDR_MULT.get(fdr, 1.0) * (1.0 - br) ** 0.6
        return adj * 2 + dt * 0.5

    def handle(self, *args, **options):
        start_gw = options['start_gw']
        end_gw   = options['end_gw']

        finished = list(
            Gameweek.objects.filter(finished=True)
            .order_by('fpl_id')
            .values_list('fpl_id', flat=True)
        )
        if end_gw:
            finished = [g for g in finished if start_gw <= g <= end_gw]
        else:
            finished = [g for g in finished if g >= start_gw]

        if not finished:
            self.stdout.write(self.style.WARNING('No finished GWs found.'))
            return

        # Load cal_log captain_fpl_id per GW (from simulation — highest fidelity)
        try:
            from predictions.models import ScorerWeights
            sw  = ScorerWeights.objects.first()
            log = (sw.calibration_log if sw else []) or []
            sim_captain_by_gw: dict[int, int] = {
                e['gw']: e['captain_fpl_id']
                for e in log
                if isinstance(e, dict) and e.get('captain_fpl_id')
            }
        except Exception:
            sim_captain_by_gw = {}

        results = []

        for gw_id in finished:
            try:
                gw = Gameweek.objects.get(fpl_id=gw_id)
            except Gameweek.DoesNotExist:
                continue

            # ── Perfect XI: best 11 by actual points (players who played) ──────
            all_stats = list(
                PlayerGameweekStats.objects
                .filter(gameweek=gw, minutes__gt=0)
                .select_related('player', 'player__team')
                .order_by('-total_points')
            )
            if len(all_stats) < 11:
                continue

            perfect_xi  = all_stats[:11]
            perfect_cap = perfect_xi[0]
            perfect_total = sum(s.total_points for s in perfect_xi) + perfect_cap.total_points  # captain ×2

            # ── Model XI: best 11 by stored predicted_points ──────────────────
            model_stats = list(
                PlayerGameweekStats.objects
                .filter(gameweek=gw, predicted_points__isnull=False)
                .select_related('player', 'player__team')
                .order_by('-predicted_points')
            )
            if len(model_stats) < 11:
                self.stdout.write(self.style.WARNING(
                    f'  GW{gw_id}: fewer than 11 predicted_points records — skipping.'
                ))
                continue

            model_xi = model_stats[:11]

            # Captain: use simulation cal_log captain when available (consistent
            # with GW History table).  Fall back to _cap_util scoring.
            sim_cap_id = sim_captain_by_gw.get(gw_id)
            model_cap  = next(
                (s for s in model_xi if s.player.fpl_id == sim_cap_id),
                None,
            )
            if model_cap is None:
                # Fall back: _cap_util scoring (FDR + blank_rate + dream_team)
                fdr_map     = self._get_fdr_map(gw)
                blank_rates = {
                    s.player_id: self._blank_rate(s.player_id, gw_id)
                    for s in model_xi
                }
                model_cap = max(model_xi, key=lambda s: self._cap_score(s, fdr_map, blank_rates))

            # Captain's actual points are doubled
            model_actual = (
                sum((s.total_points or 0) for s in model_xi)
                + (model_cap.total_points or 0)  # extra for captain double
            )

            # ── Set comparison ─────────────────────────────────────────────────
            perfect_ids = {s.player_id for s in perfect_xi}
            model_ids   = {s.player_id for s in model_xi}

            missed        = [s for s in perfect_xi    if s.player_id not in model_ids]
            wrongly_picked = [s for s in model_xi     if s.player_id not in perfect_ids]

            results.append({
                'gw':            gw_id,
                'perfect_total': perfect_total,
                'model_actual':  model_actual,
                'gap':           perfect_total - model_actual,
                'perfect_captain': perfect_cap.player.web_name,
                'model_captain':   model_cap.player.web_name,
                'captain_correct': perfect_cap.player_id == model_cap.player_id,
                'missed_players': [
                    {
                        'name':          s.player.web_name,
                        'full_name':     f"{s.player.first_name} {s.player.second_name}",
                        'position':      s.player.get_position_display(),
                        'team':          s.team_at_gw or (s.player.team.short_name if s.player.team else ''),
                        'actual_pts':    s.total_points,
                        'predicted_pts': float(s.predicted_points or 0),
                        'underrated_by': s.total_points - float(s.predicted_points or 0),
                    }
                    for s in missed
                ],
                'wrongly_picked': [
                    {
                        'name':          s.player.web_name,
                        'position':      s.player.get_position_display(),
                        'actual_pts':    s.total_points or 0,
                        'predicted_pts': float(s.predicted_points or 0),
                    }
                    for s in wrongly_picked
                ],
            })

        if not results:
            self.stdout.write(self.style.WARNING(
                'No results — make sure predicted_points are populated '
                '(run: python manage.py backfill_gw_history).'
            ))
            return

        # ── GW-by-GW table ─────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(
            f'{"GW":>4} {"Perfect":>8} {"Model":>8} {"Gap":>7}  '
            f'{"Cap OK":>10}  {"Best missed player":>25}'
        )
        self.stdout.write('-' * 78)

        for r in results:
            missed_str = r['missed_players'][0]['name'] if r['missed_players'] else '—'
            cap_label  = 'OK' if r['captain_correct'] else f'NO ({r["perfect_captain"]})'
            self.stdout.write(
                f'{r["gw"]:>4} {r["perfect_total"]:>8.1f} {r["model_actual"]:>8.1f} '
                f'{r["gap"]:>7.1f}  {cap_label:>10}  {missed_str:>25}'
            )

        # ── Aggregate missed players ────────────────────────────────────────────
        missed_counts: dict = defaultdict(lambda: {
            'count': 0, 'total_pts': 0, 'position': '', 'team': '', 'full_name': ''
        })
        for r in results:
            for p in r['missed_players']:
                d = missed_counts[p['name']]
                d['count']     += 1
                d['total_pts'] += p['actual_pts']
                d['position']   = p['position']
                d['team']       = p['team']
                d['full_name']  = p['full_name']

        self.stdout.write('')
        self.stdout.write('=== PLAYERS MODEL CONSISTENTLY MISSES (top 20) ===')
        self.stdout.write(
            f'{"Player":>28} {"Pos":>5} {"Team":>5}  '
            f'{"Missed":>7}  {"Total pts":>10}  {"Avg pts":>9}'
        )
        self.stdout.write('-' * 75)

        for name, d in sorted(missed_counts.items(), key=lambda x: -x[1]['count'])[:20]:
            avg = d['total_pts'] / d['count']
            self.stdout.write(
                f'{name:>28} {d["position"]:>5} {d["team"]:>5}  '
                f'{d["count"]:>7}  {d["total_pts"]:>10}  {avg:>9.1f}'
            )

        # ── Summary stats ──────────────────────────────────────────────────────
        n = len(results)
        correct_caps = sum(1 for r in results if r['captain_correct'])
        avg_gap      = sum(r['gap'] for r in results) / n
        avg_perfect  = sum(r['perfect_total'] for r in results) / n
        avg_model    = sum(r['model_actual']   for r in results) / n

        self.stdout.write('')
        self.stdout.write(f'GWs analysed:          {n}')
        self.stdout.write(f'Avg perfect XI score:  {avg_perfect:.1f} pts/GW')
        self.stdout.write(f'Avg model XI score:    {avg_model:.1f} pts/GW')
        self.stdout.write(f'Avg gap:               {avg_gap:.1f} pts/GW')
        self.stdout.write(f'Projected season gap:  {avg_gap * 38:.0f} pts over 38 GWs')
        self.stdout.write(
            f'Captain accuracy:      {correct_caps}/{n} GWs '
            f'({correct_caps / n * 100:.1f}%)'
        )

        # ── Most common wrongly-picked players ────────────────────────────────
        wrong_counts: dict = defaultdict(lambda: {'count': 0, 'wasted_pts': 0, 'position': ''})
        for r in results:
            for p in r['wrongly_picked']:
                d = wrong_counts[p['name']]
                d['count']      += 1
                d['wasted_pts'] += p['predicted_pts'] - p['actual_pts']
                d['position']    = p['position']

        self.stdout.write('')
        self.stdout.write('=== PLAYERS MODEL CONSISTENTLY OVERRATES (top 10) ===')
        self.stdout.write(
            f'{"Player":>28} {"Pos":>5}  {"Times over-picked":>18}  {"Total wasted pred pts":>22}'
        )
        self.stdout.write('-' * 80)
        for name, d in sorted(wrong_counts.items(), key=lambda x: -x[1]['count'])[:10]:
            self.stdout.write(
                f'{name:>28} {d["position"]:>5}  {d["count"]:>18}  {d["wasted_pts"]:>22.1f}'
            )

        # ── Save JSON ──────────────────────────────────────────────────────────
        out_path = options['output']
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Full results saved to {out_path}'))
