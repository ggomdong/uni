from django.db import models
from common.models import User


# 근무모듈
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


# 근로계약
class Contract(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='user_id', null=True)
    stand_date = models.DateField()
    type = models.CharField(max_length=20)
    check_yn = models.CharField(max_length=1)
    mon = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='mon')
    tue = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='tue')
    wed = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='wed')
    thu = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='thu')
    fri = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='fri')
    sat = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='sat')
    sun = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='sun')
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='con_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='con_mod_id')
    mod_date = models.DateTimeField()


# 근태로그
class Work(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    work_code = models.CharField(max_length=1)
    record_date = models.DateTimeField()