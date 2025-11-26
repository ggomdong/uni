from django.db import models
from django.contrib.auth.models import AbstractUser


class Branch(models.Model):
    code = models.CharField("지점코드", max_length=20, unique=True)
    name = models.CharField("지점명", max_length=100)

    # 선택: 지점 정렬 순서
    sort_order = models.PositiveIntegerField("정렬순서", default=0)

    is_active = models.BooleanField("사용여부", default=True)

    reg_date = models.DateTimeField(auto_now_add=True)
    mod_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class User(AbstractUser):
    emp_name = models.CharField(max_length=20)  # 직원명
    dept = models.CharField(max_length=50)      # 부서명
    position = models.CharField(max_length=50)  # 직위명
    join_date = models.DateField(null=True)     # 입사일자
    out_date = models.DateField(null=True, blank=True)     # 퇴사일자
    device_id = models.CharField(max_length=255, blank=True, null=True) # 기기정보

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


class Holiday(models.Model):
    holiday = models.DateField()  # 일자
    holiday_name = models.CharField(max_length=20)  # 공휴일명
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='holiday_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='holiday_mod_id')
    mod_date = models.DateTimeField()


class Business(models.Model):
    stand_date = models.DateField()
    mon = models.CharField(max_length=1)
    tue = models.CharField(max_length=1)
    wed = models.CharField(max_length=1)
    thu = models.CharField(max_length=1)
    fri = models.CharField(max_length=1)
    sat = models.CharField(max_length=1)
    sun = models.CharField(max_length=1)
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='business_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='business_mod_id')
    mod_date = models.DateTimeField()


class Code(models.Model):
    code_name = models.CharField(max_length=20)  # 코드명
    value = models.CharField(max_length=50) # 코드값
    order = models.IntegerField(null=True, blank=True)  # 출력순서
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='code_reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='code_mod_id')
    mod_date = models.DateTimeField()
