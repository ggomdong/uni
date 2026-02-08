from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0012_branch_unique_constraints"),
        ("wtm", "0010_branch_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="BranchMonthClose",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ym", models.CharField(max_length=6, verbose_name="마감월")),
                ("is_closed", models.BooleanField(default=False, verbose_name="마감여부")),
                ("closed_at", models.DateTimeField(blank=True, null=True, verbose_name="마감일시")),
                ("snapshot_json", models.JSONField(blank=True, null=True)),
                ("reg_date", models.DateTimeField(auto_now_add=True)),
                ("mod_date", models.DateTimeField(auto_now=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="month_closes",
                        to="common.branch",
                        verbose_name="지점",
                    ),
                ),
                (
                    "closed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="month_closes_closed_by",
                        to="common.user",
                    ),
                ),
            ],
            options={
                "unique_together": {("branch", "ym")},
            },
        ),
        migrations.CreateModel(
            name="MealClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("used_date", models.DateField(db_index=True, verbose_name="사용일")),
                ("amount", models.IntegerField(verbose_name="금액")),
                ("memo", models.TextField(blank=True, null=True, verbose_name="메모")),
                (
                    "source_type",
                    models.CharField(choices=[("MANUAL", "MANUAL")], default="MANUAL", max_length=20),
                ),
                ("is_deleted", models.BooleanField(default=False)),
                ("reg_date", models.DateTimeField(auto_now_add=True)),
                ("mod_date", models.DateTimeField(auto_now=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="meal_claims",
                        to="common.branch",
                        verbose_name="지점",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="meal_claims",
                        to="common.user",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MealClaimParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.IntegerField(verbose_name="분배금액")),
                (
                    "claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participants",
                        to="wtm.mealclaim",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="meal_claim_participants",
                        to="common.user",
                    ),
                ),
            ],
            options={
                "unique_together": {("claim", "user")},
            },
        ),
        migrations.AddIndex(
            model_name="branchmonthclose",
            index=models.Index(fields=["branch", "ym"], name="branch_month_close_idx"),
        ),
        migrations.AddIndex(
            model_name="mealclaim",
            index=models.Index(fields=["branch", "used_date"], name="meal_claim_branch_date_idx"),
        ),
        migrations.AddIndex(
            model_name="mealclaim",
            index=models.Index(fields=["user", "used_date"], name="meal_claim_user_date_idx"),
        ),
    ]
