"""Celery tasks for running ML predictions."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def task_run_predictions_for_gw(self, gameweek_fpl_id: int | None = None):
    """
    Run predictions for the next gameweek and store results.
    If gameweek_fpl_id is None, uses the next upcoming gameweek.
    """
    try:
        from fpl.models import Gameweek, Player, PlayerGameweekStats
        from .models import Prediction, BestPickRecommendation
        from .ml_loader import predict_player, BEST_MODEL_PER_POSITION, POSITION_MAP

        if gameweek_fpl_id:
            gw = Gameweek.objects.get(fpl_id=gameweek_fpl_id)
        else:
            gw = Gameweek.objects.filter(is_next=True).first()
            if not gw:
                gw = Gameweek.objects.filter(is_current=True).first()

        if not gw:
            logger.warning("No target gameweek found for predictions")
            return {'predictions': 0}

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
                player=player,
                gameweek=gw,
                model_name=model_type,
                defaults={'predicted_points': pred},
            )
            position_best[player.position].append((player, pred, model_type))
            count += 1

        # Store top picks per position
        for pos, picks in position_best.items():
            picks.sort(key=lambda x: x[1], reverse=True)
            for rank, (player, pred, model) in enumerate(picks[:20], start=1):
                BestPickRecommendation.objects.update_or_create(
                    gameweek=gw,
                    position=pos,
                    rank_in_position=rank,
                    defaults={
                        'player': player,
                        'predicted_points': pred,
                        'model_used': model,
                    },
                )

        logger.info(f"Predictions complete for GW{gw.fpl_id}: {count} players")
        return {'gameweek': gw.fpl_id, 'predictions': count}

    except Exception as exc:
        logger.error(f"Prediction task failed: {exc}")
        raise self.retry(exc=exc)
