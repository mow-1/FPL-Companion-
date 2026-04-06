from django.urls import path
from . import views

urlpatterns = [
    # Squad
    path('squad/', views.SquadListView.as_view(), name='manager-squad-list'),
    path('squad/current/', views.SquadDetailView.as_view(), name='manager-squad-current'),
    path('squad/<int:gw_id>/', views.SquadDetailView.as_view(), name='manager-squad-gw'),
    path('squad/sync/', views.sync_squad_from_fpl, name='manager-squad-sync'),

    # Advisor
    path('transfers/', views.transfer_suggestions_view, name='manager-transfers'),
    path('transfers/<int:suggestion_id>/accept/', views.accept_transfer_suggestion, name='manager-transfer-accept'),
    path('captain/', views.captain_suggestion_view, name='manager-captain'),
    path('chips/', views.chip_advice_view, name='manager-chips'),

    # Claude AI advice
    path('advice/', views.claude_advice_view, name='manager-claude-advice'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='manager-dashboard'),
]
