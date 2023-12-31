from django.db import models
from common.models import User


class Work(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    work_code = models.CharField(max_length=1)
    record_date = models.DateTimeField()


class Module(models.Model):
    cat = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    start_time = models.CharField(max_length=5)
    end_time = models.CharField(max_length=5)
    rest1_start_time = models.CharField(max_length=5)
    rest1_end_time = models.CharField(max_length=5)
    rest2_start_time = models.CharField(max_length=5)
    rest2_end_time = models.CharField(max_length=5)
    color = models.IntegerField()
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='mod_id')
    mod_date = models.DateTimeField()
