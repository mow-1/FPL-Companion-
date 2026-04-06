"""
Sync FPL Dream Team (Team of the Week) data for GW1–current.

Usage:
    python manage.py sync_dream_team
    python manage.py sync_dream_team --start 10 --end 29
    python manage.py sync_dream_team --gw 25

Fetches: https://fantasy.premierleague.com/api/dream-team/{gw}/
Stores:  DreamTeamEntry (gameweek, player_fpl_id, position, points, is_captain)
Reports: per-player aggregate stats after sync
"""

import logging
import time

import requests
from django.core.management.base import BaseCommand

from fpl.models import Gameweek, Player
from predictions.models import DreamTeamEntry

logger = logging.getLogger(__name__)

DREAM_TEAM_URL = "https://fantasy.premierleague.com/api/dream-team/{gw}/"
POSITION_MAP = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}


class Command(BaseCommand):
    help = "Sync FPL dream team (Team of the Week) data for all finished gameweeks."

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, default=1, help='First GW to sync (default: 1)')
        parser.add_argument('--end',   type=int, default=None, help='Last GW to sync (default: current GW)')
        parser.add_argument('--gw',    type=int, default=None, help='Sync a single GW only')

    def handle(self, *args, **options):
        # Determine GW range
        if options['gw']:
            gw_range = [options['gw']]
        else:
            start = options['start']
            end   = options['end']
            if end is None:
                current_gw = Gameweek.objects.filter(is_current=True).first()
                end = current_gw.fpl_id if current_gw else 30
            gw_range = list(range(start, end + 1))

        # Build a name/position lookup from DB players
        player_lookup = {
            p.fpl_id: p for p in Player.objects.select_related('team').all()
        }

        synced = 0
        skipped = 0
        errors = 0

        for gw in gw_range:
            url = DREAM_TEAM_URL.format(gw=gw)
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
            except requests.HTTPError as e:
                if resp.status_code == 400:
                    # GW not yet finished — skip silently
                    skipped += 1
                    continue
                self.stderr.write(f"GW{gw}: HTTP {resp.status_code} — {e}")
                errors += 1
                continue
            except Exception as e:
                self.stderr.write(f"GW{gw}: Error — {e}")
                errors += 1
                continue

            # API response: {"top_player": {"id": N, "points": N}, "team": [...]}
            team_entries = data.get('team', [])
            if not team_entries:
                self.stdout.write(f"GW{gw}: no team data in response — skipping")
                skipped += 1
                continue

            # Captain = top_player.id (highest scorer that GW)
            top_player = data.get('top_player', {})
            captain_id = top_player.get('id')

            created_count = 0
            for entry in team_entries:
                fpl_id = entry.get('element')
                points = entry.get('points', 0)
                # position field in dream-team is 1-11 (slot), not pos type
                # get actual position from DB player
                db_player = player_lookup.get(fpl_id)
                name    = db_player.web_name if db_player else f"Player#{fpl_id}"
                pos_str = POSITION_MAP.get(db_player.position, 'UNK') if db_player else 'UNK'

                DreamTeamEntry.objects.update_or_create(
                    gameweek=gw,
                    player_fpl_id=fpl_id,
                    defaults={
                        'player_name': name,
                        'position':    pos_str,
                        'points':      points,
                        'is_captain':  (fpl_id == captain_id),
                    },
                )
                created_count += 1

            self.stdout.write(f"GW{gw}: synced {created_count} dream team entries")
            synced += created_count
            time.sleep(0.3)  # polite rate limit

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {synced} entries synced across {len(gw_range)-skipped-errors} GWs. "
            f"Skipped: {skipped}, Errors: {errors}"
        ))

        # Print top 10 players by dream team appearances
        from django.db.models import Count, Q
        top = (
            DreamTeamEntry.objects
            .values('player_fpl_id', 'player_name', 'position')
            .annotate(
                appearances=Count('id'),
                captain_count=Count('id', filter=Q(is_captain=True)),
            )
            .order_by('-appearances')[:10]
        )
        self.stdout.write("\nTop 10 Dream Team players:")
        self.stdout.write(f"{'Player':25} {'Pos':4} {'Apps':5} {'Caps':5}")
        self.stdout.write("-" * 45)
        for row in top:
            self.stdout.write(
                f"{row['player_name']:25} {row['position']:4} "
                f"{row['appearances']:5} {row['captain_count']:5}"
            )
