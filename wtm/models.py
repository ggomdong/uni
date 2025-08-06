from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

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


# 근무표
class Schedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sch_user_id', null=True)
    year = models.CharField(max_length=4)
    month = models.CharField(max_length=2)
    d1 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d1')
    d2 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d2')
    d3 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d3')
    d4 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d4')
    d5 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d5')
    d6 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d6')
    d7 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d7')
    d8 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d8')
    d9 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d9')
    d10 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d10')
    d11 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d11')
    d12 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d12')
    d13 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d13')
    d14 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d14')
    d15 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d15')
    d16 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d16')
    d17 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d17')
    d18 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d18')
    d19 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d19')
    d20 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d20')
    d21 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d21')
    d22 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d22')
    d23 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d23')
    d24 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d24')
    d25 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d25')
    d26 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d26')
    d27 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d27')
    d28 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d28')
    d29 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d29')
    d30 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d30')
    d31 = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True, related_name='d31')
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sch_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sch_mod_id')
    mod_date = models.DateTimeField()


# 근태로그
class Work(models.Model):
    class WorkCode(models.TextChoices):
        IN = 'I', '출근'
        OUT = 'O', '퇴근'

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    work_code = models.CharField(max_length=1, choices=WorkCode.choices, verbose_name="근무코드")
    record_date = models.DateTimeField(auto_now_add=True)
    record_day = models.DateField(editable=False, null=False, blank=False, db_index=True)


@receiver(pre_save, sender=Work)
def set_record_day(sender, instance, **kwargs):
    if not instance.record_date:
        instance.record_date = timezone.now()
    instance.record_day = instance.record_date.date()
