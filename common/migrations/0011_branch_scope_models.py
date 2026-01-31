from django.db import migrations, models
import django.db.models.deletion


def backfill_common_branch(apps, schema_editor):
    Branch = apps.get_model("common", "Branch")
    Dept = apps.get_model("common", "Dept")
    Position = apps.get_model("common", "Position")
    Holiday = apps.get_model("common", "Holiday")
    Business = apps.get_model("common", "Business")
    Code = apps.get_model("common", "Code")

    default_branch = Branch.objects.order_by("id").first()
    if default_branch is None:
        default_branch = Branch.objects.create(code="DEFAULT", name="Default")

    def assign_branch(model_cls):
        for obj in model_cls.objects.all().select_related("reg_id__branch"):
            branch = getattr(obj, "reg_id", None) and getattr(obj.reg_id, "branch", None)
            obj.branch_id = (branch.id if branch else default_branch.id)
            obj.save(update_fields=["branch"])

    for model in (Dept, Position, Holiday, Business, Code):
        assign_branch(model)


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0010_alter_user_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="dept",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="depts",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="position",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="positions",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="holiday",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="holidays",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="business",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="businesses",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.AddField(
            model_name="code",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="codes",
                to="common.branch",
                verbose_name="지점",
            ),
        ),
        migrations.RunPython(backfill_common_branch, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="dept",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="depts",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="position",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="positions",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="holiday",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="holidays",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="business",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="businesses",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="code",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="codes",
                to="common.branch",
                verbose_name="지점",
                db_index=True,
            ),
        ),
    ]
