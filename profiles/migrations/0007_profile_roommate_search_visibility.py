from django.db import migrations, models


def hide_existing_admin_profiles(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")
    Profile.objects.filter(user__role="ADMIN").update(show_in_roommate_search=False)


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0006_rename_lifestyle_no_preference_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="show_in_roommate_search",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(
            hide_existing_admin_profiles,
            migrations.RunPython.noop,
        ),
    ]
