from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("wtm", "0012_meal_claim_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="mealclaim",
            name="memo",
        ),
    ]
