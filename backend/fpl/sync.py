"""
Sync utilities: pull data from the FPL API and upsert into the database.
Called from Celery tasks or management commands.
"""
import logging
from decimal import Decimal, InvalidOperation

from .fpl_api import get_bootstrap_static, get_fixtures, get_player_summary, get_gameweek_live, get_dream_team
from .models import Team, Gameweek, Player, PlayerGameweekStats, Fixture

logger = logging.getLogger(__name__)


def _safe_decimal(value, default=None):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return default


def sync_teams(data: list) -> int:
    count = 0
    for t in data:
        Team.objects.update_or_create(
            fpl_id=t['id'],
            defaults={
                'name': t['name'],
                'short_name': t['short_name'],
                'strength': t.get('strength', 3),
                'strength_overall_home': t.get('strength_overall_home', 0),
                'strength_overall_away': t.get('strength_overall_away', 0),
                'strength_attack_home': t.get('strength_attack_home', 0),
                'strength_attack_away': t.get('strength_attack_away', 0),
                'strength_defence_home': t.get('strength_defence_home', 0),
                'strength_defence_away': t.get('strength_defence_away', 0),
                'pulse_id': t.get('pulse_id'),
            },
        )
        count += 1
    return count


def sync_gameweeks(data: list) -> int:
    count = 0
    for gw in data:
        Gameweek.objects.update_or_create(
            fpl_id=gw['id'],
            defaults={
                'name': gw['name'],
                'deadline_time': gw.get('deadline_time'),
                'is_current': gw.get('is_current', False),
                'is_next': gw.get('is_next', False),
                'is_previous': gw.get('is_previous', False),
                'finished': gw.get('finished', False),
                'data_checked': gw.get('data_checked', False),
                'average_entry_score': gw.get('average_entry_score'),
                'highest_score': gw.get('highest_score'),
                'most_selected': gw.get('most_selected'),
                'most_transferred_in': gw.get('most_transferred_in'),
                'top_element': gw.get('top_element'),
                'transfers_made': gw.get('transfers_made'),
            },
        )
        count += 1
    return count


def sync_players(data: list) -> int:
    team_map = {t.fpl_id: t for t in Team.objects.all()}
    count = 0
    for p in data:
        team = team_map.get(p.get('team'))
        Player.objects.update_or_create(
            fpl_id=p['id'],
            defaults={
                'first_name': p['first_name'],
                'second_name': p['second_name'],
                'web_name': p['web_name'],
                'team': team,
                'position': p['element_type'],
                'status': p.get('status', 'a'),
                'news': p.get('news', ''),
                'news_added': p.get('news_added'),
                'now_cost': p.get('now_cost', 0),
                'cost_change_start': p.get('cost_change_start', 0),
                'cost_change_event': p.get('cost_change_event', 0),
                'total_points': p.get('total_points', 0),
                'minutes': p.get('minutes', 0),
                'goals_scored': p.get('goals_scored', 0),
                'assists': p.get('assists', 0),
                'clean_sheets': p.get('clean_sheets', 0),
                'goals_conceded': p.get('goals_conceded', 0),
                'own_goals': p.get('own_goals', 0),
                'penalties_saved': p.get('penalties_saved', 0),
                'penalties_missed': p.get('penalties_missed', 0),
                'yellow_cards': p.get('yellow_cards', 0),
                'red_cards': p.get('red_cards', 0),
                'saves': p.get('saves', 0),
                'bonus': p.get('bonus', 0),
                'bps': p.get('bps', 0),
                'expected_goals': _safe_decimal(p.get('expected_goals')),
                'expected_assists': _safe_decimal(p.get('expected_assists')),
                'expected_goal_involvements': _safe_decimal(p.get('expected_goal_involvements')),
                'expected_goals_conceded': _safe_decimal(p.get('expected_goals_conceded')),
                'selected_by_percent': _safe_decimal(p.get('selected_by_percent'), Decimal('0')),
                'form': _safe_decimal(p.get('form'), Decimal('0')),
                'points_per_game': _safe_decimal(p.get('points_per_game'), Decimal('0')),
                'transfers_in': p.get('transfers_in', 0),
                'transfers_out': p.get('transfers_out', 0),
                'transfers_in_event': p.get('transfers_in_event', 0),
                'transfers_out_event': p.get('transfers_out_event', 0),
                'influence': _safe_decimal(p.get('influence'), Decimal('0')),
                'creativity': _safe_decimal(p.get('creativity'), Decimal('0')),
                'threat': _safe_decimal(p.get('threat'), Decimal('0')),
                'ict_index': _safe_decimal(p.get('ict_index'), Decimal('0')),
                'influence_rank': p.get('influence_rank'),
                'creativity_rank': p.get('creativity_rank'),
                'threat_rank': p.get('threat_rank'),
                'ict_index_rank': p.get('ict_index_rank'),
                'chance_of_playing_this_round': p.get('chance_of_playing_this_round'),
                'chance_of_playing_next_round': p.get('chance_of_playing_next_round'),
                'photo': p.get('photo', ''),
                'code': p.get('code'),
            },
        )
        count += 1
    return count


def sync_fixtures(gameweek_id: int | None = None) -> int:
    fixtures_data = get_fixtures(gameweek_id)
    team_map = {t.fpl_id: t for t in Team.objects.all()}
    gw_map = {gw.fpl_id: gw for gw in Gameweek.objects.all()}
    count = 0
    for f in fixtures_data:
        Fixture.objects.update_or_create(
            fpl_id=f['id'],
            defaults={
                'gameweek': gw_map.get(f.get('event')),
                'team_h': team_map.get(f.get('team_h')),
                'team_a': team_map.get(f.get('team_a')),
                'team_h_score': f.get('team_h_score'),
                'team_a_score': f.get('team_a_score'),
                'team_h_difficulty': f.get('team_h_difficulty'),
                'team_a_difficulty': f.get('team_a_difficulty'),
                'kickoff_time': f.get('kickoff_time'),
                'finished': f.get('finished', False),
                'finished_provisional': f.get('finished_provisional', False),
                'started': f.get('started'),
            },
        )
        count += 1
    return count


def sync_player_gw_stats(player_fpl_id: int) -> int:
    summary = get_player_summary(player_fpl_id)
    history = summary.get('history', [])
    try:
        player = Player.objects.get(fpl_id=player_fpl_id)
    except Player.DoesNotExist:
        logger.warning(f"Player {player_fpl_id} not found in DB during gw stats sync")
        return 0
    gw_map = {gw.fpl_id: gw for gw in Gameweek.objects.all()}
    team_map = {t.fpl_id: t for t in Team.objects.all()}
    count = 0
    for h in history:
        gw = gw_map.get(h.get('round'))
        if not gw:
            continue
        PlayerGameweekStats.objects.update_or_create(
            player=player,
            gameweek=gw,
            defaults={
                'minutes': h.get('minutes', 0),
                'total_points': h.get('total_points', 0),
                'goals_scored': h.get('goals_scored', 0),
                'assists': h.get('assists', 0),
                'clean_sheets': h.get('clean_sheets', 0),
                'goals_conceded': h.get('goals_conceded', 0),
                'own_goals': h.get('own_goals', 0),
                'penalties_saved': h.get('penalties_saved', 0),
                'penalties_missed': h.get('penalties_missed', 0),
                'yellow_cards': h.get('yellow_cards', 0),
                'red_cards': h.get('red_cards', 0),
                'saves': h.get('saves', 0),
                'bonus': h.get('bonus', 0),
                'bps': h.get('bps', 0),
                'influence': _safe_decimal(h.get('influence'), Decimal('0')),
                'creativity': _safe_decimal(h.get('creativity'), Decimal('0')),
                'threat': _safe_decimal(h.get('threat'), Decimal('0')),
                'ict_index': _safe_decimal(h.get('ict_index'), Decimal('0')),
                'expected_goals': _safe_decimal(h.get('expected_goals')),
                'expected_assists': _safe_decimal(h.get('expected_assists')),
                'expected_goal_involvements': _safe_decimal(h.get('expected_goal_involvements')),
                'expected_goals_conceded': _safe_decimal(h.get('expected_goals_conceded')),
                'starts': h.get('starts', 0),
                'was_home': h.get('was_home'),
                'opponent_team': team_map.get(h.get('opponent_team')),
                'kickoff_time': h.get('kickoff_time'),
                'value': h.get('value', 0),
                'selected': h.get('selected', 0),
                'transfers_balance': h.get('transfers_balance', 0),
                # Record player's team at this GW (current team; overridden by
                # Phase 1.5 in backfill_gw_history if vaastav historical data exists)
                'team_at_gw': player.team.name if player.team else '',
            },
        )
        count += 1
    return count


def sync_dream_team_counts() -> int:
    """
    Fetch the Dream Team for every finished GW and count how many times
    each player has appeared. Stores result in Player.dream_team_count.
    This is a valuable signal for the ML scorer:
      - Frequent Dream Team players have explosive ceiling + consistency
      - Used to boost captain score for high-ceiling players
    """
    finished_gws = Gameweek.objects.filter(finished=True).values_list('fpl_id', flat=True)
    counts: dict[int, int] = {}  # fpl_id → count

    for gw_id in finished_gws:
        try:
            data = get_dream_team(gw_id)
            for entry in data.get('team', []):
                pid = entry.get('element')
                if pid:
                    counts[pid] = counts.get(pid, 0) + 1
        except Exception as e:
            logger.warning(f"Could not fetch dream team for GW{gw_id}: {e}")

    updated = 0
    for fpl_id, count in counts.items():
        updated += Player.objects.filter(fpl_id=fpl_id).update(dream_team_count=count)

    # Zero out players not in any dream team
    Player.objects.exclude(fpl_id__in=counts.keys()).update(dream_team_count=0)
    logger.info(f"Dream team counts updated for {len(counts)} players")
    return updated


def full_sync() -> dict:
    """Pull everything from FPL API and sync to DB."""
    logger.info("Starting full FPL sync...")
    bootstrap = get_bootstrap_static()

    teams_synced = sync_teams(bootstrap.get('teams', []))
    logger.info(f"Teams synced: {teams_synced}")

    gw_synced = sync_gameweeks(bootstrap.get('events', []))
    logger.info(f"Gameweeks synced: {gw_synced}")

    players_synced = sync_players(bootstrap.get('elements', []))
    logger.info(f"Players synced: {players_synced}")

    fixtures_synced = sync_fixtures()
    logger.info(f"Fixtures synced: {fixtures_synced}")

    dream_team_synced = sync_dream_team_counts()
    logger.info(f"Dream team counts synced: {dream_team_synced}")

    return {
        'teams': teams_synced,
        'gameweeks': gw_synced,
        'players': players_synced,
        'fixtures': fixtures_synced,
        'dream_team': dream_team_synced,
    }
