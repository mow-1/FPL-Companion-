from django.contrib import admin
from .models import Prediction, BestPickRecommendation


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('player', 'gameweek', 'model_name', 'predicted_points', 'created_at')
    list_filter = ('model_name', 'gameweek', 'player__position')
    search_fields = ('player__web_name',)
    ordering = ('-predicted_points',)


@admin.register(BestPickRecommendation)
class BestPickAdmin(admin.ModelAdmin):
    list_display = ('gameweek', 'position', 'rank_in_position', 'player', 'predicted_points', 'model_used')
    list_filter = ('gameweek', 'position')
    ordering = ('gameweek', 'position', 'rank_in_position')
