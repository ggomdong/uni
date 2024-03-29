# Generated by Django 4.2.6 on 2024-01-30 23:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wtm', '0002_contract'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contract',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='user_id', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.CharField(max_length=4)),
                ('month', models.CharField(max_length=2)),
                ('reg_date', models.DateTimeField()),
                ('mod_date', models.DateTimeField()),
                ('d1', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d1', to='wtm.module')),
                ('d10', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d10', to='wtm.module')),
                ('d11', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d11', to='wtm.module')),
                ('d12', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d12', to='wtm.module')),
                ('d13', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d13', to='wtm.module')),
                ('d14', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d14', to='wtm.module')),
                ('d15', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d15', to='wtm.module')),
                ('d16', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d16', to='wtm.module')),
                ('d17', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d17', to='wtm.module')),
                ('d18', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d18', to='wtm.module')),
                ('d19', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d19', to='wtm.module')),
                ('d2', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d2', to='wtm.module')),
                ('d20', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d20', to='wtm.module')),
                ('d21', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d21', to='wtm.module')),
                ('d22', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d22', to='wtm.module')),
                ('d23', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d23', to='wtm.module')),
                ('d24', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d24', to='wtm.module')),
                ('d25', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d25', to='wtm.module')),
                ('d26', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d26', to='wtm.module')),
                ('d27', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d27', to='wtm.module')),
                ('d28', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d28', to='wtm.module')),
                ('d29', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d29', to='wtm.module')),
                ('d3', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d3', to='wtm.module')),
                ('d30', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d30', to='wtm.module')),
                ('d31', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d31', to='wtm.module')),
                ('d4', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d4', to='wtm.module')),
                ('d5', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d5', to='wtm.module')),
                ('d6', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d6', to='wtm.module')),
                ('d7', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d7', to='wtm.module')),
                ('d8', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d8', to='wtm.module')),
                ('d9', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='d9', to='wtm.module')),
                ('mod_id', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sch_mod_id', to=settings.AUTH_USER_MODEL)),
                ('reg_id', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sch_reg_id', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sch_user_id', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
