"""
Management command: python manage.py sync_fpl [--players]
Syncs FPL data from the official API.
"""
from django.core.management.base import BaseCommand
from fpl.sync import full_sync, sync_player_gw_stats
from fpl.models import Player


class Command(BaseCommand):
    help = 'Sync FPL data (teams, players, gameweeks, fixtures) from the official API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--players',
            action='store_true',
            help='Also sync per-player per-gameweek stats (slow — one request per player).',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting FPL sync...')
        result = full_sync()
        self.stdout.write(self.style.SUCCESS(
            f"Sync complete: {result['teams']} teams, {result['gameweeks']} gameweeks, "
            f"{result['players']} players, {result['fixtures']} fixtures."
        ))

        if options['players']:
            self.stdout.write('Syncing per-player GW stats (this may take a few minutes)...')
            player_ids = list(Player.objects.values_list('fpl_id', flat=True))
            total = 0
            for i, pid in enumerate(player_ids, 1):
                try:
                    count = sync_player_gw_stats(pid)
                    total += count
                    if i % 50 == 0:
                        self.stdout.write(f'  Processed {i}/{len(player_ids)} players...')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Player {pid} failed: {e}'))
            self.stdout.write(self.style.SUCCESS(f'Player GW stats synced: {total} records.'))
