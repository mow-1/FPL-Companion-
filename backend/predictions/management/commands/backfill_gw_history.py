"""
Management command: python manage.py backfill_gw_history

Two-phase backfill for GW History:

  Phase 1 — Sync player GW stats from FPL API
    Calls sync_player_gw_stats(fpl_id) for every player in the DB.
    Populates PlayerGameweekStats with actual_points, minutes, xG, xA, etc.
    Skip with --skip-sync if PlayerGameweekStats is already populated.

  Phase 2 — Run the learning simulation GW1 → last finished GW
    Calls simulate_learning_progression(start_gw, reset=True).
    For each GW: scores players, builds best XI, fetches actuals,
    calibrates weights, appends entry to ScorerWeights.calibration_log.
    /predictions/gw-history/ reads directly from that log.

Usage:
  python manage.py backfill_gw_history                     # full backfill
  python manage.py backfill_gw_history --skip-sync         # simulation only (stats already in DB)
  python manage.py backfill_gw_history --start-gw 10       # simulate from GW10 onward
  python manage.py backfill_gw_history --end-gw 20         # simulate up to GW20 only
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Backfill GW history: sync player stats then run learning simulation.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-sync',
            action='store_true',
            help='Skip Phase 1 (FPL API sync) — use if PlayerGameweekStats already populated.',
        )
        parser.add_argument(
            '--start-gw',
            type=int,
            default=1,
            help='First GW to include in the learning simulation (default: 1).',
        )
        parser.add_argument(
            '--end-gw',
            type=int,
            default=None,
            help='Last GW to include in the learning simulation (default: last finished GW).',
        )
        parser.add_argument(
            '--recalibrate',
            action='store_true',
            help=(
                'Pre-compute position-specific calibration multipliers from the existing '
                'calibration_log, clear all predicted_points from PlayerGameweekStats, '
                'then re-run the full simulation (GW1 onward) applying those multipliers. '
                'Use this after the calibration multipliers in ml_loader.py have been updated.'
            ),
        )

    def handle(self, *args, **options):
        from fpl.models import Player, Gameweek
        from fpl.sync import sync_player_gw_stats, sync_dream_team_counts
        from predictions.optimizer import simulate_learning_progression
        from predictions.scorer_weights import invalidate_cache

        # ── Recalibrate: pre-compute multipliers, clear old predictions ────────
        cal_multipliers = None
        if options.get('recalibrate'):
            self.stdout.write(self.style.HTTP_INFO(
                'Recalibrate mode — loading position-specific calibration multipliers...'
            ))
            from predictions.ml_loader import compute_calibration_multipliers, _calibration_cache
            import predictions.ml_loader as _ml
            # Force recompute from existing calibration_log (before it's cleared by reset)
            _ml._calibration_cache = None
            cal_multipliers = compute_calibration_multipliers()

            if all(v == 1.0 for v in cal_multipliers.values()):
                self.stdout.write(self.style.WARNING(
                    '  No calibration_log data found — multipliers are all 1.0. '
                    'Run a normal backfill first, then re-run with --recalibrate.'
                ))
            else:
                self.stdout.write(
                    f'  Calibration multipliers: '
                    + ', '.join(f'{p}={v:.4f}' for p, v in sorted(cal_multipliers.items()))
                )

            # Clear per-player predicted_points so the fresh run populates clean values
            from fpl.models import PlayerGameweekStats
            n_cleared = PlayerGameweekStats.objects.exclude(
                predicted_points=None
            ).update(predicted_points=None)
            self.stdout.write(f'  Cleared predicted_points for {n_cleared} PlayerGameweekStats records.')

            # Force full simulation from GW1 regardless of --start-gw
            options['start_gw'] = 1
            options['skip_sync'] = True   # stats are already in DB; just re-run simulation
            self.stdout.write(
                '  Skipping Phase 1 sync (stats already in DB). '
                'Re-running simulation from GW1 with calibrated multipliers.\n'
            )

        # ── Phase 1: Sync player GW stats ─────────────────────────────────────
        if options['skip_sync']:
            self.stdout.write('Skipping Phase 1 (--skip-sync set).')
        else:
            self.stdout.write(self.style.HTTP_INFO('Phase 1 — Syncing player GW stats from FPL API...'))

            player_ids = list(Player.objects.values_list('fpl_id', flat=True))
            if not player_ids:
                self.stdout.write(self.style.WARNING(
                    '  No players in DB. Run: python manage.py sync_fpl first.'
                ))
                return

            self.stdout.write(f'  Fetching stats for {len(player_ids)} players...')
            total_records = 0
            errors = 0
            for i, pid in enumerate(player_ids, 1):
                try:
                    count = sync_player_gw_stats(pid)
                    total_records += count
                except Exception as e:
                    errors += 1
                    if errors <= 5:   # only show first 5 to avoid spamming
                        self.stdout.write(self.style.WARNING(f'    Player {pid} failed: {e}'))
                if i % 100 == 0:
                    self.stdout.write(f'    {i}/{len(player_ids)} players processed, {total_records} records so far...')

            self.stdout.write(self.style.SUCCESS(
                f'  Phase 1 complete: {total_records} PlayerGameweekStats records synced'
                + (f', {errors} players failed.' if errors else '.')
            ))

            # Sync dream team counts (boosts captain utility score in scorer)
            self.stdout.write('  Syncing dream team counts...')
            try:
                dt_count = sync_dream_team_counts()
                self.stdout.write(f'  Dream team counts updated for {dt_count} players.')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Dream team sync failed (non-fatal): {e}'))

        # NOTE: team_at_gw uses current season team assignment (player.team.name)
        # This is correct for 2025-26 season stats.
        # Historical cross-season team tracking would require a separate
        # PlayerTeamHistory model — documented as future work.

        # ── Verify we have stats before running simulation ─────────────────────
        from fpl.models import PlayerGameweekStats
        stats_count = PlayerGameweekStats.objects.count()
        if stats_count == 0:
            self.stdout.write(self.style.ERROR(
                'PlayerGameweekStats is still empty after sync. '
                'Check your FPL API connectivity and re-run without --skip-sync.'
            ))
            return
        self.stdout.write(f'  PlayerGameweekStats: {stats_count} rows ready.')

        # ── Phase 2: Run learning simulation ──────────────────────────────────
        start_gw = options['start_gw']
        end_gw   = options['end_gw']

        finished_gws = list(
            Gameweek.objects.filter(finished=True)
            .order_by('fpl_id')
            .values_list('fpl_id', flat=True)
        )
        if not finished_gws:
            self.stdout.write(self.style.WARNING('No finished GWs found in DB.'))
            return

        effective_end = end_gw or finished_gws[-1]
        target_count  = len([g for g in finished_gws if start_gw <= g <= effective_end])

        self.stdout.write(self.style.HTTP_INFO(
            f'Phase 2 — Running learning simulation GW{start_gw}–GW{effective_end} '
            f'({target_count} gameweeks)...'
        ))

        # Invalidate in-memory weight cache so we start fresh
        invalidate_cache()

        results = simulate_learning_progression(
            start_gw=start_gw,
            end_gw=end_gw,
            reset=(start_gw == 1),   # only full-reset when starting from GW1
            cal_multipliers=cal_multipliers,
        )

        if not results:
            self.stdout.write(self.style.WARNING(
                'simulate_learning_progression returned no results. '
                'Check that PlayerGameweekStats rows exist for those GWs.'
            ))
            return

        # ── Print summary table ────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Phase 2 complete — {len(results)} GWs processed.'))
        self.stdout.write('')
        self.stdout.write(f'  {"GW":>4}  {"Pred":>6}  {"Actual":>6}  {"Diff":>6}  {"MAE":>6}  Captain')
        self.stdout.write(f'  {"-"*4}  {"-"*6}  {"-"*6}  {"-"*6}  {"-"*6}  -------')

        ok_count = sum(1 for r in results if 'error' not in r)
        err_count = len(results) - ok_count
        diffs = [abs(r['diff']) for r in results if 'diff' in r and r['diff'] is not None]

        for r in results:
            if 'error' in r:
                self.stdout.write(f'  GW{r["gw"]:>2}  (error: {r["error"]})')
                continue
            diff_str = f'{r["diff"]:+.1f}' if r['diff'] is not None else '–'
            mae_str  = f'{r["mae"]:.3f}'   if r['mae']  is not None else '–'
            self.stdout.write(
                f'  {r["gw"]:>4}  {r["predicted_pts"]:>6.1f}  {r["actual_pts"]:>6.1f}'
                f'  {diff_str:>6}  {mae_str:>6}  {r.get("captain","–")}'
            )

        self.stdout.write('')
        if diffs:
            avg_diff = sum(diffs) / len(diffs)
            self.stdout.write(
                f'  Avg |diff|: {avg_diff:.1f} pts   '
                f'  GWs OK: {ok_count}   Errors: {err_count}'
            )

        # ── Verify calibration_log saved correctly ─────────────────────────────
        from predictions.models import ScorerWeights
        from fpl.models import PlayerGameweekStats
        import statistics as _stats

        sw = ScorerWeights.objects.first()
        log_len = len(sw.calibration_log) if sw else 0
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'ScorerWeights.calibration_log: {log_len} entries saved. '
            f'/predictions/gw-history/ is now ready.'
        ))

        # Per-player predicted_points verification
        preds = list(
            PlayerGameweekStats.objects
            .filter(predicted_points__isnull=False)
            .values_list('predicted_points', flat=True)
        )
        if preds:
            avg_pred = _stats.mean(preds)
            # Only look at "active" players (predicted > 2.0) to exclude zeros
            # from injured/unavailable/no-history players
            active_preds = [p for p in preds if p > 2.0]
            avg_active = _stats.mean(active_preds) if active_preds else 0.0
            self.stdout.write(
                f'PlayerGameweekStats.predicted_points: {len(preds)} records total '
                f'(avg all={avg_pred:.2f}, avg active>{len(active_preds)} records={avg_active:.2f})'
                + (' [calibrated]' if cal_multipliers else '')
            )

        # Team-level signed bias (most meaningful check)
        log_entries = (sw.calibration_log or []) if sw else []
        log_valid = [e for e in log_entries if e.get('predicted_pts') and e.get('actual_pts')]
        if log_valid:
            mean_diff = sum(e['actual_pts'] - e['predicted_pts'] for e in log_valid) / len(log_valid)
            self.stdout.write(
                f'Team-level mean diff (actual-predicted): {mean_diff:+.1f} pts/GW '
                f'({"near-zero = calibrated" if abs(mean_diff) < 3 else "still biased — consider re-running --recalibrate"})'
            )
        else:
            self.stdout.write(self.style.WARNING(
                'No PlayerGameweekStats.predicted_points found. '
                'The simulation may not have written per-player scores.'
            ))
