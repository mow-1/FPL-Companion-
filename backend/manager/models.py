from django.conf import settings
from django.db import models
from fpl.models import Player, Gameweek, Team


class Squad(models.Model):
    """A user's FPL squad snapshot for a given gameweek."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='squads')
    gameweek = models.ForeignKey(Gameweek, on_delete=models.CASCADE, related_name='squads')
    bank = models.FloatField(default=0.0, help_text="Money in bank (£m)")
    free_transfers = models.PositiveSmallIntegerField(default=1)
    overall_rank = models.PositiveIntegerField(null=True, blank=True)
    gameweek_points = models.IntegerField(null=True, blank=True)
    total_points = models.IntegerField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'gameweek')
        ordering = ['-gameweek__fpl_id']

    def __str__(self):
        return f"{self.user.email} GW{self.gameweek.fpl_id}"


class SquadPlayer(models.Model):
    """A player in a user's squad."""
    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    is_captain = models.BooleanField(default=False)
    is_vice_captain = models.BooleanField(default=False)
    is_starter = models.BooleanField(default=True)  # False = bench
    bench_order = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-4 for bench players
    purchase_price = models.PositiveIntegerField(default=0, help_text="Price when bought (10x)")
    selling_price = models.PositiveIntegerField(default=0, help_text="Current sell price (10x)")

    class Meta:
        unique_together = ('squad', 'player')

    def __str__(self):
        role = 'C' if self.is_captain else ('VC' if self.is_vice_captain else '')
        return f"{self.player.web_name} {role}".strip()


class TransferSuggestion(models.Model):
    """AI-generated transfer suggestion for a user."""
    REASON_CHOICES = [
        ('form', 'In Form'),
        ('fixture', 'Good Fixtures'),
        ('injury', 'Injury Replacement'),
        ('price_rise', 'Price Rise'),
        ('differential', 'Differential Pick'),
        ('prediction', 'High Predicted Points'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transfer_suggestions')
    gameweek = models.ForeignKey(Gameweek, on_delete=models.CASCADE)
    player_out = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='suggested_out')
    player_in = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='suggested_in')
    points_gain = models.FloatField(help_text="Estimated points gain over next GW")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    reason_detail = models.TextField(blank=True)
    cost_impact = models.FloatField(default=0.0, help_text="Positive = profit, negative = loss in bank")
    accepted = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-points_gain']

    def __str__(self):
        return f"OUT: {self.player_out.web_name} → IN: {self.player_in.web_name} (+{self.points_gain:.1f}pts)"


class CaptainSuggestion(models.Model):
    """Captain/vice-captain recommendation for a gameweek."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='captain_suggestions')
    gameweek = models.ForeignKey(Gameweek, on_delete=models.CASCADE)
    captain = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='captain_picks')
    vice_captain = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='vc_picks')
    captain_predicted = models.FloatField()
    vc_predicted = models.FloatField()
    differential_captain = models.ForeignKey(
        Player, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='differential_captain_picks',
        help_text="Low-ownership high-upside alternative"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'gameweek')

    def __str__(self):
        return f"{self.user.email} GW{self.gameweek.fpl_id} C:{self.captain.web_name}"


class ChipAdvice(models.Model):
    """Chip usage recommendations."""
    CHIP_CHOICES = [
        ('wildcard', 'Wildcard'),
        ('freehit', 'Free Hit'),
        ('benchboost', 'Bench Boost'),
        ('triplecaptain', 'Triple Captain'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chip_advice')
    gameweek = models.ForeignKey(Gameweek, on_delete=models.CASCADE)
    chip = models.CharField(max_length=20, choices=CHIP_CHOICES)
    recommended = models.BooleanField(default=False)
    score = models.FloatField(default=0.0, help_text="0-10 confidence score")
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'gameweek', 'chip')
