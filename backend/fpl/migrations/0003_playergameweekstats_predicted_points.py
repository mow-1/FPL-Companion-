from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fpl', '0002_dream_team_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='playergameweekstats',
            name='predicted_points',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
