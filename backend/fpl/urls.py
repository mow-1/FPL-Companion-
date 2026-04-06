from django.urls import path
from . import views

urlpatterns = [
    # Reference data
    path('teams/', views.TeamListView.as_view(), name='fpl-teams'),
    path('gameweeks/', views.GameweekListView.as_view(), name='fpl-gameweeks'),
    path('gameweeks/current/', views.CurrentGameweekView.as_view(), name='fpl-current-gw'),

    # Players
    path('players/', views.PlayerListView.as_view(), name='fpl-players'),
    path('players/<int:fpl_id>/', views.PlayerDetailView.as_view(), name='fpl-player-detail'),
    path('players/<int:fpl_id>/history/', views.PlayerHistoryView.as_view(), name='fpl-player-history'),

    # Fixtures
    path('fixtures/', views.FixtureListView.as_view(), name='fpl-fixtures'),

    # FPL API proxies
    path('manager/<int:manager_id>/', views.fpl_manager_proxy, name='fpl-manager'),
    path('manager/<int:manager_id>/history/', views.fpl_manager_history_proxy, name='fpl-manager-history'),
    path('manager/<int:manager_id>/picks/<int:gameweek>/', views.fpl_manager_picks_proxy, name='fpl-manager-picks'),

    # Admin
    path('sync/', views.trigger_sync, name='fpl-sync'),
]
