"""
Management command: python manage.py run_predictions [--gw GW_ID]
Runs ML predictions for the next gameweek and stores results in DB.
"""
from django.core.management.base import BaseCommand
from predictions.tasks import task_run_predictions_for_gw
from fpl.models import Gameweek


class Command(BaseCommand):
    help = 'Run ML predictions for the next (or specified) gameweek.'

    def add_arguments(self, parser):
        parser.add_argument('--gw', type=int, default=None, help='Gameweek FPL ID to predict for.')

    def handle(self, *args, **options):
        gw_id = options['gw']
        if gw_id:
            try:
                gw = Gameweek.objects.get(fpl_id=gw_id)
            except Gameweek.DoesNotExist:
                self.stderr.write(f'Gameweek {gw_id} not found. Run sync_fpl first.')
                return
            self.stdout.write(f'Running predictions for {gw.name}...')
        else:
            gw = Gameweek.objects.filter(is_next=True).first()
            if not gw:
                gw = Gameweek.objects.filter(is_current=True).first()
            if not gw:
                self.stderr.write('No upcoming gameweek found. Run sync_fpl first.')
                return
            self.stdout.write(f'Running predictions for {gw.name}...')

        # Run synchronously (not via Celery) in management command context
        from predictions.ml_loader import predict_player, BEST_MODEL_PER_POSITION, POSITION_MAP
        from fpl.models import Player, PlayerGameweekStats
        from predictions.models import Prediction, BestPickRecommendation

        players = Player.objects.select_related('team').all()
        count = 0
        position_best: dict[int, list] = {1: [], 2: [], 3: [], 4: []}

        for player in players:
            pos_name = POSITION_MAP.get(player.position, 'MID')
            model_type = BEST_MODEL_PER_POSITION.get(pos_name, 'lstm_base')
            gw_stats = PlayerGameweekStats.objects.filter(player=player).order_by('-gameweek__fpl_id')
            pred = predict_player(player, gw_stats, model_type)
            if pred is None:
                continue
            Prediction.objects.update_or_create(
                player=player, gameweek=gw, model_name=model_type,
                defaults={'predicted_points': pred},
            )
            position_best[player.position].append((player, pred, model_type))
            count += 1

        for pos, picks in position_best.items():
            picks.sort(key=lambda x: x[1], reverse=True)
            for rank, (player, pred, model) in enumerate(picks[:20], start=1):
                BestPickRecommendation.objects.update_or_create(
                    gameweek=gw, position=pos, rank_in_position=rank,
                    defaults={'player': player, 'predicted_points': pred, 'model_used': model},
                )

        self.stdout.write(self.style.SUCCESS(f'Predictions complete: {count} players predicted for {gw.name}.'))
