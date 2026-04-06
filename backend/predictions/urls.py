from django.urls import path
from . import views

urlpatterns = [
    path('', views.PredictionListView.as_view(), name='predictions-list'),
    path('best-picks/', views.BestPicksView.as_view(), name='predictions-best-picks'),
    path('player/<int:fpl_id>/', views.predict_player_view, name='predictions-player'),
    path('run/', views.predict_all_view, name='predictions-run'),
    path('trigger/', views.trigger_predictions, name='predictions-trigger'),
    path('best-team/', views.best_team_view, name='predictions-best-team'),
    path('track-record/', views.track_record_view, name='predictions-track-record'),
    path('gw-history/',   views.gw_history_view,   name='predictions-gw-history'),
    path('differentials/', views.differentials_view, name='predictions-differentials'),
    path('community-compare/', views.community_compare_view, name='predictions-community-compare'),
]
