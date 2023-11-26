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
