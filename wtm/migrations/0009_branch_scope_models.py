from django.db import migrations, models
import django.db.models.deletion


def backfill_wtm_branch(apps, schema_editor):
    Branch = apps.get_model("common", "Branch")
    Module = apps.get_model("wtm", "Module")
    Contract = apps.get_model("wtm", "Contract")
    Schedule = apps.get_model("wtm", "Schedule")
    Work = apps.get_model("wtm", "Work")

    default_branch = Branch.objects.order_by("id").first()
    if default_branch is None:
        default_branch = Branch.objects.create(code="DEFAULT", name="Default")

    for module in Module.objects.all().select_related("reg_id__branch"):
        branch = getattr(module, "reg_id", None) and getattr(module.reg_id, "branch", None)
        module.branch_id = (branch.id if branch else default_branch.id)
        module.save(update_fields=["branch"])

    for contract in Contract.objects.all().select_related("user__branch", "reg_id__branch"):
        branch = None
        if contract.user and getattr(contract.user, "branch", None):
            branch = contract.user.branch
        elif contract.reg_id and getattr(contract.reg_id, "branch", None):
            branch = contract.reg_id.branch
        contract.branch_id = (branch.id if branch else default_branch.id)
        contract.save(update_fields=["branch"])

    for schedule in Schedule.objects.all().select_related("user__branch", "reg_id__branch"):
        branch = None
        if schedule.user and getattr(schedule.user, "branch", None):
            branch = schedule.user.branch
        elif schedule.reg_id and getattr(schedule.reg_id, "branch", None):
            branch = schedule.reg_id.branch
        schedule.branch_id = (branch.id if branch else default_branch.id)
        schedule.save(update_fields=["branch"])

    for work in Work.objects.all().select_related("user__branch"):
        branch = getattr(work.user, "branch", None) if work.user else None
        work.branch_id = (branch.id if branch else default_branch.id)
        work.save(update_fields=["branch"])


class Migration(migrations.Migration):

    dependencies = [
        ("wtm", "0008_module_order"),
        ("common", "0010_alter_user_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="module",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="modules",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contracts",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="schedule",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="schedules",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="work",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="works",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.RunPython(backfill_wtm_branch, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="module",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="modules",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="contract",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contracts",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="schedule",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="schedules",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="work",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="works",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
    ]
