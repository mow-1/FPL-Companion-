from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    fpl_team_id = models.PositiveIntegerField(null=True, blank=True, help_text="Official FPL team ID")
    fpl_team_name = models.CharField(max_length=100, blank=True)
    favourite_team = models.PositiveIntegerField(null=True, blank=True)
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email
