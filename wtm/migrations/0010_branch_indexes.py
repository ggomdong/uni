from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wtm", "0009_branch_scope_models"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="module",
            index=models.Index(fields=["branch", "order"], name="module_branch_order_idx"),
        ),
        migrations.AddIndex(
            model_name="contract",
            index=models.Index(
                fields=["branch", "user_id", "stand_date"],
                name="contract_branch_user_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="schedule",
            index=models.Index(
                fields=["branch", "year", "month", "user_id"],
                name="schedule_branch_ym_user_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="work",
            index=models.Index(fields=["branch", "record_day"], name="work_branch_day_idx"),
        ),
        migrations.AddIndex(
            model_name="work",
            index=models.Index(
                fields=["branch", "user_id", "record_day"],
                name="work_branch_user_day_idx",
            ),
        ),
    ]
