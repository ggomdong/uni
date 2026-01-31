from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pybo", "0002_branch_scope_models"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="question",
            index=models.Index(fields=["branch", "create_date"], name="question_branch_created_idx"),
        ),
        migrations.AddIndex(
            model_name="answer",
            index=models.Index(fields=["branch", "create_date"], name="answer_branch_created_idx"),
        ),
    ]
