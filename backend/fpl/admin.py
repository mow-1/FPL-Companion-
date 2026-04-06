from django.contrib import admin
from .models import Team, Gameweek, Player, PlayerGameweekStats, Fixture


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'strength', 'fpl_id')
    search_fields = ('name', 'short_name')


@admin.register(Gameweek)
class GameweekAdmin(admin.ModelAdmin):
    list_display = ('name', 'deadline_time', 'is_current', 'is_next', 'finished', 'average_entry_score')
    list_filter = ('is_current', 'is_next', 'finished')


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('web_name', 'team', 'get_position_display', 'now_cost', 'total_points', 'form', 'status')
    list_filter = ('position', 'status', 'team')
    search_fields = ('web_name', 'first_name', 'second_name')
    ordering = ('-total_points',)


@admin.register(PlayerGameweekStats)
class PlayerGameweekStatsAdmin(admin.ModelAdmin):
    list_display = ('player', 'gameweek', 'total_points', 'minutes', 'goals_scored', 'assists')
    list_filter = ('gameweek',)
    search_fields = ('player__web_name',)


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'kickoff_time', 'finished', 'team_h_score', 'team_a_score')
    list_filter = ('gameweek', 'finished')
