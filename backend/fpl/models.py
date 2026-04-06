from django.db import models


class Team(models.Model):
    fpl_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=10)
    strength = models.PositiveSmallIntegerField(default=3)
    strength_overall_home = models.PositiveIntegerField(default=0)
    strength_overall_away = models.PositiveIntegerField(default=0)
    strength_attack_home = models.PositiveIntegerField(default=0)
    strength_attack_away = models.PositiveIntegerField(default=0)
    strength_defence_home = models.PositiveIntegerField(default=0)
    strength_defence_away = models.PositiveIntegerField(default=0)
    pulse_id = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Gameweek(models.Model):
    fpl_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=30)
    deadline_time = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    is_next = models.BooleanField(default=False)
    is_previous = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    data_checked = models.BooleanField(default=False)
    average_entry_score = models.FloatField(null=True, blank=True)
    highest_score = models.PositiveIntegerField(null=True, blank=True)
    most_selected = models.PositiveIntegerField(null=True, blank=True)
    most_transferred_in = models.PositiveIntegerField(null=True, blank=True)
    top_element = models.PositiveIntegerField(null=True, blank=True)
    transfers_made = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['fpl_id']

    def __str__(self):
        return self.name


class Player(models.Model):
    POSITION_CHOICES = [
        (1, 'GK'),
        (2, 'DEF'),
        (3, 'MID'),
        (4, 'FWD'),
    ]

    fpl_id = models.PositiveIntegerField(unique=True)
    first_name = models.CharField(max_length=100)
    second_name = models.CharField(max_length=100)
    web_name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='players')
    position = models.PositiveSmallIntegerField(choices=POSITION_CHOICES)
    status = models.CharField(max_length=1, default='a')  # a=available, d=doubt, i=injured, s=suspended, u=unavailable
    news = models.TextField(blank=True)
    news_added = models.DateTimeField(null=True, blank=True)

    # Pricing
    now_cost = models.PositiveIntegerField(default=0)  # stored as 10x (e.g. 65 = £6.5m)
    cost_change_start = models.IntegerField(default=0)
    cost_change_event = models.IntegerField(default=0)

    # Season totals
    total_points = models.IntegerField(default=0)
    minutes = models.PositiveIntegerField(default=0)
    goals_scored = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    clean_sheets = models.PositiveIntegerField(default=0)
    goals_conceded = models.PositiveIntegerField(default=0)
    own_goals = models.PositiveIntegerField(default=0)
    penalties_saved = models.PositiveIntegerField(default=0)
    penalties_missed = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)
    saves = models.PositiveIntegerField(default=0)
    bonus = models.PositiveIntegerField(default=0)
    bps = models.IntegerField(default=0)

    # Expected stats
    expected_goals = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    expected_assists = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    expected_goal_involvements = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    expected_goals_conceded = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Ownership & form
    selected_by_percent = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    form = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    points_per_game = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    transfers_in = models.PositiveIntegerField(default=0)
    transfers_out = models.PositiveIntegerField(default=0)
    transfers_in_event = models.PositiveIntegerField(default=0)
    transfers_out_event = models.PositiveIntegerField(default=0)

    # ICT
    influence = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    creativity = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    threat = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    ict_index = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    influence_rank = models.PositiveIntegerField(null=True, blank=True)
    creativity_rank = models.PositiveIntegerField(null=True, blank=True)
    threat_rank = models.PositiveIntegerField(null=True, blank=True)
    ict_index_rank = models.PositiveIntegerField(null=True, blank=True)

    # Chance of playing
    chance_of_playing_this_round = models.PositiveSmallIntegerField(null=True, blank=True)
    chance_of_playing_next_round = models.PositiveSmallIntegerField(null=True, blank=True)

    # Dream Team (Team of the Week) appearances this season
    dream_team_count = models.PositiveSmallIntegerField(default=0)

    photo = models.CharField(max_length=50, blank=True)
    code = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-total_points']

    def __str__(self):
        return f"{self.web_name} ({self.get_position_display()})"

    @property
    def price(self):
        return self.now_cost / 10

    @property
    def full_name(self):
        return f"{self.first_name} {self.second_name}"


class PlayerGameweekStats(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='gw_stats')
    gameweek = models.ForeignKey(Gameweek, on_delete=models.CASCADE, related_name='player_stats')

    minutes = models.PositiveIntegerField(default=0)
    total_points = models.IntegerField(default=0)
    goals_scored = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    clean_sheets = models.PositiveIntegerField(default=0)
    goals_conceded = models.PositiveIntegerField(default=0)
    own_goals = models.PositiveIntegerField(default=0)
    penalties_saved = models.PositiveIntegerField(default=0)
    penalties_missed = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)
    saves = models.PositiveIntegerField(default=0)
    bonus = models.PositiveIntegerField(default=0)
    bps = models.IntegerField(default=0)
    influence = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    creativity = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    threat = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    ict_index = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    expected_goals = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    expected_assists = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    expected_goal_involvements = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    expected_goals_conceded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    starts = models.PositiveSmallIntegerField(default=0)
    was_home = models.BooleanField(null=True, blank=True)
    opponent_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    kickoff_time = models.DateTimeField(null=True, blank=True)
    value = models.PositiveIntegerField(default=0)
    selected = models.PositiveIntegerField(default=0)
    transfers_balance = models.IntegerField(default=0)
    team_at_gw = models.CharField(max_length=50, blank=True)
    predicted_points = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('player', 'gameweek')
        ordering = ['gameweek__fpl_id']

    def __str__(self):
        return f"{self.player.web_name} GW{self.gameweek.fpl_id}: {self.total_points}pts"


class Fixture(models.Model):
    fpl_id = models.PositiveIntegerField(unique=True)
    gameweek = models.ForeignKey(Gameweek, on_delete=models.SET_NULL, null=True, related_name='fixtures')
    team_h = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='home_fixtures')
    team_a = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='away_fixtures')
    team_h_score = models.PositiveSmallIntegerField(null=True, blank=True)
    team_a_score = models.PositiveSmallIntegerField(null=True, blank=True)
    team_h_difficulty = models.PositiveSmallIntegerField(null=True, blank=True)
    team_a_difficulty = models.PositiveSmallIntegerField(null=True, blank=True)
    kickoff_time = models.DateTimeField(null=True, blank=True)
    finished = models.BooleanField(default=False)
    finished_provisional = models.BooleanField(default=False)
    started = models.BooleanField(null=True, blank=True)
    provisional_start_time = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['kickoff_time']

    def __str__(self):
        return f"GW{self.gameweek.fpl_id if self.gameweek else '?'}: {self.team_h} vs {self.team_a}"
