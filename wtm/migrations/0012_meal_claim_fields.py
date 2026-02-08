from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wtm", "0011_meal_claims"),
    ]

    operations = [
        migrations.AddField(
            model_name="mealclaim",
            name="approval_no",
            field=models.CharField(default="", max_length=64, verbose_name="승인번호"),
        ),
        migrations.AddField(
            model_name="mealclaim",
            name="restaurant_name",
            field=models.CharField(default="", max_length=120, verbose_name="식당명"),
        ),
        migrations.AddIndex(
            model_name="mealclaim",
            index=models.Index(fields=["branch", "approval_no"], name="meal_claim_branch_approval_idx"),
        ),
    ]
