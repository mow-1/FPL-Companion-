from rest_framework import serializers
from fpl.serializers import PlayerListSerializer
from .models import Squad, SquadPlayer, TransferSuggestion, CaptainSuggestion, ChipAdvice


class SquadPlayerSerializer(serializers.ModelSerializer):
    player = PlayerListSerializer(read_only=True)
    player_id = serializers.IntegerField(write_only=True)
    sell_price = serializers.SerializerMethodField()

    class Meta:
        model = SquadPlayer
        fields = (
            'id', 'player', 'player_id', 'is_captain', 'is_vice_captain',
            'is_starter', 'bench_order', 'purchase_price', 'selling_price', 'sell_price',
        )

    def get_sell_price(self, obj):
        return obj.selling_price / 10 if obj.selling_price else obj.player.price


class SquadSerializer(serializers.ModelSerializer):
    players = SquadPlayerSerializer(many=True, read_only=True)
    gameweek_name = serializers.CharField(source='gameweek.name', read_only=True)
    squad_value = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Squad
        fields = (
            'id', 'gameweek', 'gameweek_name', 'bank', 'free_transfers',
            'overall_rank', 'gameweek_points', 'total_points',
            'squad_value', 'total_value', 'players', 'synced_at',
        )

    def get_squad_value(self, obj):
        return sum(sp.player.price for sp in obj.players.select_related('player').all())

    def get_total_value(self, obj):
        return self.get_squad_value(obj) + obj.bank


class TransferSuggestionSerializer(serializers.ModelSerializer):
    player_out_name       = serializers.CharField(source='player_out.web_name',             read_only=True)
    player_out_price      = serializers.FloatField(source='player_out.price',                read_only=True)
    player_out_form       = serializers.FloatField(source='player_out.form',                 read_only=True)
    player_out_team       = serializers.CharField(source='player_out.team.short_name',       read_only=True)
    player_out_position   = serializers.CharField(source='player_out.get_position_display',  read_only=True)
    player_out_photo_code = serializers.IntegerField(source='player_out.code',               read_only=True)
    player_in_name        = serializers.CharField(source='player_in.web_name',               read_only=True)
    player_in_price       = serializers.FloatField(source='player_in.price',                 read_only=True)
    player_in_form        = serializers.FloatField(source='player_in.form',                  read_only=True)
    player_in_team        = serializers.CharField(source='player_in.team.short_name',        read_only=True)
    player_in_position    = serializers.CharField(source='player_in.get_position_display',   read_only=True)
    player_in_photo_code  = serializers.IntegerField(source='player_in.code',                read_only=True)
    player_in_selected    = serializers.FloatField(source='player_in.selected_by_percent',   read_only=True)
    gameweek_name         = serializers.CharField(source='gameweek.name',                    read_only=True)

    class Meta:
        model = TransferSuggestion
        fields = (
            'id', 'gameweek', 'gameweek_name',
            'player_out', 'player_out_name', 'player_out_price', 'player_out_form',
            'player_out_team', 'player_out_position', 'player_out_photo_code',
            'player_in', 'player_in_name', 'player_in_price', 'player_in_form',
            'player_in_team', 'player_in_position', 'player_in_photo_code',
            'player_in_selected', 'points_gain', 'reason', 'reason_detail',
            'cost_impact', 'accepted', 'created_at',
        )


class CaptainSuggestionSerializer(serializers.ModelSerializer):
    captain_name       = serializers.CharField(source='captain.web_name', read_only=True)
    captain_team       = serializers.CharField(source='captain.team.short_name', read_only=True)
    captain_photo_code = serializers.IntegerField(source='captain.code', read_only=True)
    captain_position   = serializers.CharField(source='captain.get_position_display', read_only=True)
    vc_name            = serializers.CharField(source='vice_captain.web_name', read_only=True)
    vc_team            = serializers.CharField(source='vice_captain.team.short_name', read_only=True)
    vc_photo_code      = serializers.IntegerField(source='vice_captain.code', read_only=True)
    vc_position        = serializers.CharField(source='vice_captain.get_position_display', read_only=True)
    differential_name       = serializers.CharField(source='differential_captain.web_name', read_only=True)
    differential_photo_code = serializers.IntegerField(source='differential_captain.code', read_only=True)
    differential_position   = serializers.CharField(source='differential_captain.get_position_display', read_only=True)
    differential_selected   = serializers.FloatField(
        source='differential_captain.selected_by_percent', read_only=True
    )
    gameweek_name = serializers.CharField(source='gameweek.name', read_only=True)

    class Meta:
        model = CaptainSuggestion
        fields = (
            'id', 'gameweek', 'gameweek_name',
            'captain', 'captain_name', 'captain_team', 'captain_photo_code',
            'captain_position', 'captain_predicted',
            'vice_captain', 'vc_name', 'vc_team', 'vc_photo_code',
            'vc_position', 'vc_predicted',
            'differential_captain', 'differential_name', 'differential_photo_code',
            'differential_position', 'differential_selected',
            'created_at',
        )


class ChipAdviceSerializer(serializers.ModelSerializer):
    gameweek_name = serializers.CharField(source='gameweek.name', read_only=True)

    class Meta:
        model = ChipAdvice
        fields = ('id', 'gameweek', 'gameweek_name', 'chip', 'recommended', 'score', 'reason', 'created_at')
