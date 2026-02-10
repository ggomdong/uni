from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wtm", "0013_remove_mealclaim_memo"),
    ]

    operations = [
        migrations.RenameField(
            model_name="mealclaim",
            old_name="restaurant_name",
            new_name="merchant_name",
        ),
        migrations.AlterField(
            model_name="mealclaim",
            name="merchant_name",
            field=models.CharField(default="", max_length=120, verbose_name="????"),
        ),
    ]
