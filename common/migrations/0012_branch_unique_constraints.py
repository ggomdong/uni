from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0011_branch_scope_models"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="dept",
            constraint=models.UniqueConstraint(
                fields=("branch", "dept_name"),
                name="dept_unique_branch_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="position",
            constraint=models.UniqueConstraint(
                fields=("branch", "position_name"),
                name="position_unique_branch_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="holiday",
            constraint=models.UniqueConstraint(
                fields=("branch", "holiday"),
                name="holiday_unique_branch_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="business",
            constraint=models.UniqueConstraint(
                fields=("branch", "stand_date"),
                name="business_unique_branch_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="code",
            constraint=models.UniqueConstraint(
                fields=("branch", "code_name", "value"),
                name="code_unique_branch_name_value",
            ),
        ),
    ]
