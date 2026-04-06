from rest_framework import serializers
from .models import Prediction, BestPickRecommendation


class PredictionSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.web_name', read_only=True)
    player_team = serializers.CharField(source='player.team.short_name', read_only=True)
    player_position = serializers.CharField(source='player.get_position_display', read_only=True)
    player_price = serializers.FloatField(source='player.price', read_only=True)
    player_photo_code = serializers.IntegerField(source='player.code', read_only=True)
    gameweek_name = serializers.CharField(source='gameweek.name', read_only=True)

    class Meta:
        model = Prediction
        fields = (
            'id', 'player', 'player_name', 'player_team', 'player_position',
            'player_price', 'player_photo_code', 'gameweek', 'gameweek_name',
            'model_name', 'predicted_points', 'confidence_low', 'confidence_high',
            'created_at',
        )


class BestPickSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.web_name', read_only=True)
    player_team = serializers.CharField(source='player.team.short_name', read_only=True)
    player_position = serializers.CharField(source='player.get_position_display', read_only=True)
    player_price = serializers.FloatField(source='player.price', read_only=True)
    player_fpl_id = serializers.IntegerField(source='player.fpl_id', read_only=True)
    player_photo_code = serializers.IntegerField(source='player.code', read_only=True)
    player_status = serializers.CharField(source='player.status', read_only=True)
    player_news = serializers.CharField(source='player.news', read_only=True)
    player_selected_by = serializers.FloatField(source='player.selected_by_percent', read_only=True)
    player_form = serializers.FloatField(source='player.form', read_only=True)

    class Meta:
        model = BestPickRecommendation
        fields = (
            'id', 'gameweek', 'position', 'player', 'player_fpl_id',
            'player_name', 'player_team', 'player_position', 'player_price',
            'player_photo_code', 'player_status', 'player_news',
            'player_selected_by', 'player_form',
            'predicted_points', 'rank_in_position', 'model_used', 'updated_at',
        )
