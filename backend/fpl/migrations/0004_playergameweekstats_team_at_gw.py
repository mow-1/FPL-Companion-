from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fpl', '0003_playergameweekstats_predicted_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='playergameweekstats',
            name='team_at_gw',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
