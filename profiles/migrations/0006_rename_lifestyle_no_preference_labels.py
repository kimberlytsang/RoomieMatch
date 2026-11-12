from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("profiles", "0005_rename_pet_no_preference_label")]

    operations = [
        migrations.AlterField(
            model_name="preference",
            name="party_preference",
            field=models.CharField(
                choices=[
                    ("NO_PREFERENCE", "No preference with parties"),
                    ("NO_PARTIES", "No parties"),
                    ("SOMETIMES", "Parties sometimes"),
                    ("OFTEN", "Parties often"),
                ],
                default="NO_PREFERENCE",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="preference",
            name="sleep_preference",
            field=models.CharField(
                choices=[
                    ("NO_PREFERENCE", "No preference with sleep"),
                    ("EARLY", "Sleep early"),
                    ("LATE", "Sleep late"),
                    ("VARIES", "Sleep time varies"),
                ],
                default="NO_PREFERENCE",
                max_length=20,
            ),
        ),
    ]
