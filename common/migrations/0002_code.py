# Generated by Django 4.2.6 on 2024-02-13 22:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Code',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_name', models.CharField(max_length=20)),
                ('value', models.CharField(max_length=50)),
                ('order', models.IntegerField(blank=True, null=True)),
                ('reg_date', models.DateTimeField()),
                ('mod_date', models.DateTimeField()),
                ('mod_id', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='code_mod_id', to=settings.AUTH_USER_MODEL)),
                ('reg_id', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='code_reg_id', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
