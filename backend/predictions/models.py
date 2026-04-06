from django.db import models
from fpl.models import Player, Gameweek


class Prediction(models.Model):
    """Stores ML model predictions for a player in a gameweek."""
    MODEL_CHOICES = [
        ('lstm_base', 'LSTM Base'),
        ('lstm_enhanced', 'LSTM Enhanced'),
        ('gru_base', 'GRU Base'),
        ('gru_enhanced', 'GRU Enhanced'),
        ('ensemble_base', 'Ensemble Base'),
        ('ensemble_enhanced', 'Ensemble Enhanced'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='predictions')
    gameweek = models.ForeignKey(Gameweek, on_delete=models.CASCADE, related_name='predictions')
    model_name = models.CharField(max_length=30, choices=MODEL_CHOICES)
    predicted_points = models.FloatField()
    confidence_low = models.FloatField(null=True, blank=True)
    confidence_high = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'gameweek', 'model_name')
        ordering = ['-predicted_points']

    def __str__(self):
        return f"{self.player.web_name} GW{self.gameweek.fpl_id} [{self.model_name}]: {self.predicted_points:.2f}pts"


class BestPickRecommendation(models.Model):
    """Top predicted players per position per gameweek (derived from Predictions)."""
    POSITION_CHOICES = [(1, 'GK'), (2, 'DEF'), (3, 'MID'), (4, 'FWD')]

    gameweek = models.ForeignKey(Gameweek, on_delete=models.CASCADE, related_name='best_picks')
    position = models.PositiveSmallIntegerField(choices=POSITION_CHOICES)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    predicted_points = models.FloatField()
    rank_in_position = models.PositiveSmallIntegerField()
    model_used = models.CharField(max_length=30)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('gameweek', 'position', 'rank_in_position')
        ordering = ['position', 'rank_in_position']


class DreamTeamEntry(models.Model):
    """
    Stores FPL community dream team (Team of the Week) entries per GW.
    Populated by: python manage.py sync_dream_team
    Used by Layer 3 optimizer to add captaincy signal from historical data.
    """
    gameweek = models.PositiveSmallIntegerField(db_index=True)
    player_fpl_id = models.PositiveIntegerField(db_index=True)
    player_name = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=3, blank=True)   # GK/DEF/MID/FWD
    points = models.PositiveSmallIntegerField(default=0)
    is_captain = models.BooleanField(default=False)

    class Meta:
        unique_together = ('gameweek', 'player_fpl_id')
        ordering = ['gameweek', '-points']

    def __str__(self):
        cap = ' (C)' if self.is_captain else ''
        return f"GW{self.gameweek}: {self.player_name}{cap} — {self.points}pts"


class ScorerWeights(models.Model):
    """
    Single-row store for the adaptive scorer's learnable weights.
    Calibrated after each finished GW by calibrate_after_gw().
    The weights dict maps weight names to float values — see scorer_weights.py
    for the full schema and bounds.
    """
    weights = models.JSONField(default=dict)
    last_calibrated_gw = models.PositiveSmallIntegerField(null=True, blank=True)
    calibration_log = models.JSONField(default=list)   # list of per-GW summaries
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Scorer weights'

    def __str__(self):
        return f"ScorerWeights (last GW: {self.last_calibrated_gw})"
