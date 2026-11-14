from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("profiles", "0003_restore_story_budget_ranges")]

    operations = [
        migrations.AddField(
            model_name="preference",
            name="party_preference",
            field=models.CharField(
                choices=[
                    ("NO_PREFERENCE", "No preference"),
                    ("NO_PARTIES", "No parties"),
                    ("SOMETIMES", "Parties sometimes"),
                    ("OFTEN", "Parties often"),
                ],
                default="NO_PREFERENCE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="preference",
            name="sleep_preference",
            field=models.CharField(
                choices=[
                    ("NO_PREFERENCE", "No preference"),
                    ("EARLY", "Sleep early"),
                    ("LATE", "Sleep late"),
                    ("VARIES", "Sleep time varies"),
                ],
                default="NO_PREFERENCE",
                max_length=20,
            ),
        ),
    ]
