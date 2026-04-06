from django.contrib import admin
from .models import Squad, SquadPlayer, TransferSuggestion, CaptainSuggestion, ChipAdvice


class SquadPlayerInline(admin.TabularInline):
    model = SquadPlayer
    extra = 0
    raw_id_fields = ('player',)


@admin.register(Squad)
class SquadAdmin(admin.ModelAdmin):
    list_display = ('user', 'gameweek', 'bank', 'free_transfers', 'gameweek_points', 'total_points')
    list_filter = ('gameweek',)
    search_fields = ('user__email',)
    inlines = [SquadPlayerInline]


@admin.register(TransferSuggestion)
class TransferSuggestionAdmin(admin.ModelAdmin):
    list_display = ('user', 'gameweek', 'player_out', 'player_in', 'points_gain', 'reason', 'accepted')
    list_filter = ('reason', 'accepted', 'gameweek')
    search_fields = ('user__email', 'player_out__web_name', 'player_in__web_name')


@admin.register(CaptainSuggestion)
class CaptainSuggestionAdmin(admin.ModelAdmin):
    list_display = ('user', 'gameweek', 'captain', 'captain_predicted', 'vice_captain', 'vc_predicted')
    list_filter = ('gameweek',)


@admin.register(ChipAdvice)
class ChipAdviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'gameweek', 'chip', 'recommended', 'score')
    list_filter = ('chip', 'recommended', 'gameweek')
