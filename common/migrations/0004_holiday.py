# Generated by Django 4.2.6 on 2024-03-09 22:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0003_position_dept'),
    ]

    operations = [
        migrations.CreateModel(
            name='Holiday',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('holiday', models.DateField()),
                ('holiday_name', models.CharField(max_length=20)),
                ('reg_date', models.DateTimeField()),
                ('mod_id', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='holiday_mod_id', to=settings.AUTH_USER_MODEL)),
                ('reg_id', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='holiday_reg_id', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
