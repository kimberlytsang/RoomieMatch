from django.db import migrations, models


OLD_TO_NEW = {
    "UNDER_500": "UNDER_1500",
    "B501_1000": "B1501_2000",
    "B1001_1500": "B2001_2500",
    "B1501_2000": "B2501_3000",
    "B2001_2500": "B3001_3500",
    "B2501_3000": "B3501_4000",
    "OVER_3000": "OVER_4000",
}


def raise_budget_ranges(apps, schema_editor):
    preference = apps.get_model("profiles", "Preference")
    for old_value, new_value in OLD_TO_NEW.items():
        preference.objects.filter(budget_range=old_value).update(budget_range=new_value)


def restore_budget_ranges(apps, schema_editor):
    preference = apps.get_model("profiles", "Preference")
    for old_value, new_value in OLD_TO_NEW.items():
        preference.objects.filter(budget_range=new_value).update(budget_range=old_value)


class Migration(migrations.Migration):
    dependencies = [("profiles", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="preference",
            name="budget_range",
            field=models.CharField(
                choices=[
                    ("UNDER_1500", "Under $1,500"),
                    ("B1501_2000", "$1,501-$2,000"),
                    ("B2001_2500", "$2,001-$2,500"),
                    ("B2501_3000", "$2,501-$3,000"),
                    ("B3001_3500", "$3,001-$3,500"),
                    ("B3501_4000", "$3,501-$4,000"),
                    ("OVER_4000", "$4,001+"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(raise_budget_ranges, restore_budget_ranges),
    ]
