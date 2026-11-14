from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("profiles", "0004_add_lifestyle_preferences")]

    operations = [
        migrations.AlterField(
            model_name="preference",
            name="pets_preference",
            field=models.CharField(
                choices=[
                    ("PET_FRIENDLY", "Pet friendly"),
                    ("NO_PETS", "No pets"),
                    ("NO_PREFERENCE", "No preference with pets"),
                ],
                max_length=20,
            ),
        ),
    ]
