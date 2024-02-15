from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    emp_name = models.CharField(max_length=20)  # 직원명
    dept = models.CharField(max_length=50)      # 부서명
    position = models.CharField(max_length=50)  # 직위명
    join_date = models.DateField(null=True)     # 입사일자
    out_date = models.DateField(null=True, blank=True)     # 퇴사일자

    emp_name.verbose_name = "직원명"
    dept.verbose_name = "부서명"
    position.verbose_name = "직위명"
    join_date.verbose_name = "입사일자"
    out_date.verbose_name = "퇴사일자"


class Dept(models.Model):
    dept_name = models.CharField(max_length=20)  # 부서명
    order = models.IntegerField(null=True, blank=True)  # 출력순서
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='dept_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='dept_mod_id')
    mod_date = models.DateTimeField()


class Position(models.Model):
    position_name = models.CharField(max_length=20)  # 직위명
    order = models.IntegerField(null=True, blank=True)  # 출력순서
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='position_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='position_mod_id')
    mod_date = models.DateTimeField()


class Code(models.Model):
    code_name = models.CharField(max_length=20)  # 코드명
    value = models.CharField(max_length=50) # 코드값
    order = models.IntegerField(null=True, blank=True)  # 출력순서
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='code_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='code_mod_id')
    mod_date = models.DateTimeField()
