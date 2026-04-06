"""
Fixes team_at_gw for all PlayerGameweekStats using the official FPL API.

For each player, fetches their full GW history from:
  https://fantasy.premierleague.com/api/element-summary/{fpl_id}/

History entries contain 'fixture' (fixture FPL id) and 'was_home'.
Cross-referenced against the FPL fixtures endpoint to get the player's
exact team each GW — since the history API does NOT expose 'team' directly.

Usage:
  python manage.py fix_team_at_gw --player "Semenyo"   # single player test
  python manage.py fix_team_at_gw --all                # all players (~7 min)
"""
import time
import requests
from django.core.management.base import BaseCommand
from fpl.models import Player, PlayerGameweekStats

FPL_ELEMENT_URL  = "https://fantasy.premierleague.com/api/element-summary/{}/"
FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES_URL  = "https://fantasy.premierleague.com/api/fixtures/"


class Command(BaseCommand):
    help = 'Fix team_at_gw using FPL API element-summary (fixture + was_home inference)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--player',
            type=str,
            help='Fix only this player (web_name fragment, e.g. "Semenyo")',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fix all players (slow — one API call per player, ~7 min for 800 players)',
        )

    def handle(self, *args, **options):
        # ── Load team map from bootstrap ───────────────────────────────────────
        self.stdout.write('Loading team map from FPL bootstrap...')
        bootstrap  = requests.get(FPL_BOOTSTRAP_URL, timeout=15).json()
        team_map   = {t['id']: t['short_name'] for t in bootstrap['teams']}
        self.stdout.write(f'  {len(team_map)} teams loaded: {list(team_map.values())}')

        # ── Load all fixtures to resolve fixture_id → (team_h, team_a) ────────
        self.stdout.write('Loading fixtures from FPL API...')
        all_fixtures = requests.get(FPL_FIXTURES_URL, timeout=15).json()
        # {fixture_fpl_id: (team_h_id, team_a_id)}
        fixture_map  = {f['id']: (f['team_h'], f['team_a']) for f in all_fixtures}
        self.stdout.write(f'  {len(fixture_map)} fixtures loaded')

        # ── Select players ─────────────────────────────────────────────────────
        if options['player']:
            players = Player.objects.filter(web_name__icontains=options['player'])
            if not players.exists():
                # fallback to second_name
                players = Player.objects.filter(second_name__icontains=options['player'])
        elif options['all']:
            players = Player.objects.filter(fpl_id__isnull=False).order_by('id')
        else:
            self.stdout.write(self.style.ERROR(
                'Specify --player "Name" to test one player, or --all to fix everyone.'
            ))
            return

        total = players.count()
        self.stdout.write(f'Fixing team_at_gw for {total} player(s)...\n')

        fixed  = 0
        errors = 0

        for i, player in enumerate(players, 1):
            if not player.fpl_id:
                continue

            # Safe name for Windows cp1252 console
            safe_name = player.web_name.encode('ascii', errors='replace').decode('ascii')

            try:
                resp = requests.get(FPL_ELEMENT_URL.format(player.fpl_id), timeout=10)
                if resp.status_code != 200:
                    errors += 1
                    self.stdout.write(self.style.WARNING(
                        f'  [{i}/{total}] {safe_name}: HTTP {resp.status_code}'
                    ))
                    continue

                history = resp.json().get('history', [])
                if not history:
                    continue

                # Build {gw_round: team_short} from fixture + was_home
                gw_team_map: dict[int, str] = {}
                for entry in history:
                    fixture_id = entry.get('fixture')
                    was_home   = entry.get('was_home')
                    gw         = entry.get('round')
                    if fixture_id is None or was_home is None or gw is None:
                        continue
                    team_h_id, team_a_id = fixture_map.get(fixture_id, (None, None))
                    player_team_id = team_h_id if was_home else team_a_id
                    if player_team_id:
                        team_short = team_map.get(player_team_id, '')
                        if team_short:
                            gw_team_map[gw] = team_short

                if not gw_team_map:
                    continue

                # Update DB records for matching GWs
                stats = list(
                    PlayerGameweekStats.objects
                    .filter(player=player, gameweek__fpl_id__in=list(gw_team_map.keys()))
                    .select_related('gameweek')
                )

                updates = []
                for stat in stats:
                    correct_team = gw_team_map.get(stat.gameweek.fpl_id)
                    if correct_team and stat.team_at_gw != correct_team:
                        stat.team_at_gw = correct_team
                        updates.append(stat)

                if updates:
                    PlayerGameweekStats.objects.bulk_update(updates, ['team_at_gw'], batch_size=200)
                    fixed += len(updates)
                    self.stdout.write(
                        f'  [{i}/{total}] {safe_name}: '
                        f'fixed {len(updates)} GW records '
                        f'(teams: {sorted(set(gw_team_map.values()))})'
                    )
                else:
                    if options['player']:
                        self.stdout.write(
                            f'  [{i}/{total}] {safe_name}: '
                            f'all {len(stats)} records already correct'
                        )

                # Rate limit — be polite to FPL API
                if options['all']:
                    time.sleep(0.4)

            except Exception as e:
                errors += 1
                safe_err = str(e).encode('ascii', errors='replace').decode('ascii')
                self.stdout.write(self.style.ERROR(f'  [{i}/{total}] {safe_name}: {safe_err}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Fixed {fixed} records across {total} player(s). Errors: {errors}.'
        ))
        if fixed > 0:
            self.stdout.write(
                'Re-run calibration to incorporate corrected team assignments:\n'
                '  python manage.py backfill_gw_history --recalibrate'
            )
