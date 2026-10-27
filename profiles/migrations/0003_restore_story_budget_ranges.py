from django.db import migrations, models


# Migration 0002 temporarily raised the ranges.  Keep it intact because it
# may already have been applied by a teammate, then restore the Sprint 2/
# User Story values in this follow-up migration.
RAISED_TO_STORY = {
    "UNDER_1500": "UNDER_500",
    "B1501_2000": "B501_1000",
    "B2001_2500": "B1001_1500",
    "B2501_3000": "B1501_2000",
    "B3001_3500": "B2001_2500",
    "B3501_4000": "B2501_3000",
    "OVER_4000": "OVER_3000",
}


def restore_story_budget_ranges(apps, schema_editor):
    preference = apps.get_model("profiles", "Preference")
    for raised_value, story_value in RAISED_TO_STORY.items():
        preference.objects.filter(budget_range=raised_value).update(budget_range=story_value)


def reapply_raised_budget_ranges(apps, schema_editor):
    preference = apps.get_model("profiles", "Preference")
    for raised_value, story_value in RAISED_TO_STORY.items():
        preference.objects.filter(budget_range=story_value).update(budget_range=raised_value)


class Migration(migrations.Migration):
    dependencies = [("profiles", "0002_raise_budget_ranges")]

    operations = [
        migrations.RunPython(restore_story_budget_ranges, reapply_raised_budget_ranges),
        migrations.AlterField(
            model_name="preference",
            name="budget_range",
            field=models.CharField(
                choices=[
                    ("UNDER_500", "Under $500"),
                    ("B501_1000", "$501-$1,000"),
                    ("B1001_1500", "$1,001-$1,500"),
                    ("B1501_2000", "$1,501-$2,000"),
                    ("B2001_2500", "$2,001-$2,500"),
                    ("B2501_3000", "$2,501-$3,000"),
                    ("OVER_3000", "$3,001+"),
                ],
                max_length=20,
            ),
        ),
    ]
