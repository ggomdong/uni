from django.db import migrations, models
import django.db.models.deletion


def backfill_pybo_branch(apps, schema_editor):
    Question = apps.get_model("pybo", "Question")
    Answer = apps.get_model("pybo", "Answer")

    for question in Question.objects.all().select_related("author__branch"):
        branch = getattr(question.author, "branch", None)
        if branch:
            question.branch_id = branch.id
            question.save(update_fields=["branch"])

    for answer in Answer.objects.all().select_related("question__branch"):
        branch = getattr(answer.question, "branch", None)
        if branch:
            answer.branch_id = branch.id
            answer.save(update_fields=["branch"])


class Migration(migrations.Migration):

    dependencies = [
        ("pybo", "0001_initial"),
        ("common", "0010_alter_user_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="questions",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="answer",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="answers",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.RunPython(backfill_pybo_branch, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="question",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="questions",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="answer",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="answers",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
    ]
