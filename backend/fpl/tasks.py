"""Celery tasks for FPL data synchronization."""
from celery import shared_task
from .sync import full_sync, sync_fixtures, sync_player_gw_stats
from .models import Player, Gameweek
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_full_sync(self):
    """Full sync of all FPL data. Run once per gameweek deadline."""
    try:
        result = full_sync()
        logger.info(f"Full sync complete: {result}")
        return result
    except Exception as exc:
        logger.error(f"Full sync failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def task_sync_current_gw_fixtures(self):
    """Sync fixtures for the current gameweek (run during gameweek for live updates)."""
    try:
        current_gw = Gameweek.objects.filter(is_current=True).first()
        if not current_gw:
            logger.warning("No current gameweek found")
            return {'fixtures': 0}
        count = sync_fixtures(current_gw.fpl_id)
        return {'fixtures': count, 'gameweek': current_gw.fpl_id}
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def task_sync_all_player_gw_stats(self):
    """Sync per-player per-GW stats for all players. Heavy task."""
    try:
        player_ids = list(Player.objects.values_list('fpl_id', flat=True))
        total = 0
        for pid in player_ids:
            try:
                count = sync_player_gw_stats(pid)
                total += count
            except Exception as e:
                logger.warning(f"Failed to sync player {pid}: {e}")
        return {'player_gw_stats_synced': total}
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def task_sync_player_gw_stats(player_fpl_id: int):
    """Sync GW stats for a single player."""
    count = sync_player_gw_stats(player_fpl_id)
    return {'player': player_fpl_id, 'gw_stats_synced': count}
