"""
Wrapper for the official Fantasy Premier League API.
Base URL: https://fantasy.premierleague.com/api/
"""
import requests
from typing import Any

FPL_BASE = 'https://fantasy.premierleague.com/api'
TIMEOUT = 15

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; FPL-Manager-Assistant/1.0)',
}


def _get(endpoint: str) -> Any:
    url = f"{FPL_BASE}{endpoint}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_bootstrap_static() -> dict:
    """Main FPL bootstrap endpoint: teams, players, gameweeks, etc."""
    return _get('/bootstrap-static/')


def get_fixtures(gameweek: int | None = None) -> list:
    """All fixtures, or filtered by gameweek."""
    endpoint = '/fixtures/'
    if gameweek:
        endpoint += f'?event={gameweek}'
    return _get(endpoint)


def get_player_summary(player_id: int) -> dict:
    """Per-player history and upcoming fixtures."""
    return _get(f'/element-summary/{player_id}/')


def get_gameweek_live(gameweek: int) -> dict:
    """Live points for a specific gameweek."""
    return _get(f'/event/{gameweek}/live/')


def get_manager_info(manager_id: int) -> dict:
    """Public manager info."""
    return _get(f'/entry/{manager_id}/')


def get_manager_history(manager_id: int) -> dict:
    """Manager season history, chips used, etc."""
    return _get(f'/entry/{manager_id}/history/')


def get_manager_picks(manager_id: int, gameweek: int) -> dict:
    """Manager picks for a specific gameweek."""
    return _get(f'/entry/{manager_id}/event/{gameweek}/picks/')


def get_manager_transfers(manager_id: int) -> list:
    """All transfers made by a manager."""
    return _get(f'/entry/{manager_id}/transfers/')


def get_dream_team(gameweek: int) -> dict:
    """Dream team for a gameweek."""
    return _get(f'/dream-team/{gameweek}/')
