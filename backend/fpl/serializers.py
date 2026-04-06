from rest_framework import serializers
from .models import Team, Gameweek, Player, PlayerGameweekStats, Fixture


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'


class GameweekSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gameweek
        fields = '__all__'


class PlayerListSerializer(serializers.ModelSerializer):
    team_name  = serializers.CharField(source='team.short_name', read_only=True)
    team_short = serializers.CharField(source='team.short_name', read_only=True)
    position_name = serializers.CharField(source='get_position_display', read_only=True)
    price = serializers.FloatField(read_only=True)

    class Meta:
        model = Player
        fields = (
            'id', 'fpl_id', 'web_name', 'full_name', 'team', 'team_name', 'team_short',
            'position', 'position_name', 'price', 'now_cost', 'status', 'news',
            'total_points', 'form', 'points_per_game', 'selected_by_percent',
            'expected_goals', 'expected_assists', 'expected_goal_involvements',
            'ict_index', 'transfers_in_event', 'transfers_out_event',
            'chance_of_playing_this_round', 'chance_of_playing_next_round',
            'code',
        )


class PlayerDetailSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    position_name = serializers.CharField(source='get_position_display', read_only=True)
    price = serializers.FloatField(read_only=True)

    class Meta:
        model = Player
        fields = '__all__'


class PlayerGameweekStatsSerializer(serializers.ModelSerializer):
    gameweek_name = serializers.CharField(source='gameweek.name', read_only=True)
    opponent_name = serializers.CharField(source='opponent_team.short_name', read_only=True)

    class Meta:
        model = PlayerGameweekStats
        fields = '__all__'


class FixtureSerializer(serializers.ModelSerializer):
    team_h_name = serializers.CharField(source='team_h.name', read_only=True)
    team_a_name = serializers.CharField(source='team_a.name', read_only=True)
    team_h_short = serializers.CharField(source='team_h.short_name', read_only=True)
    team_a_short = serializers.CharField(source='team_a.short_name', read_only=True)
    gameweek_name = serializers.CharField(source='gameweek.name', read_only=True)

    class Meta:
        model = Fixture
        fields = '__all__'
