from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from common.models import Branch, User


# 근로모듈
class Module(models.Model):
    cat = models.CharField("구분", max_length=20)
    name = models.CharField("근로명", max_length=50)
    start_time = models.CharField("시업시각", max_length=5)
    end_time = models.CharField("종업시각", max_length=5)
    rest1_start_time = models.CharField("휴게1시작시각", max_length=5)
    rest1_end_time = models.CharField("휴게1종료시각", max_length=5)
    rest2_start_time = models.CharField("휴게2시작시각", max_length=5)
    rest2_end_time = models.CharField("휴게2종료시각", max_length=5)
    meal_amount = models.PositiveIntegerField("식대(원)", null=True, blank=True)
    color = models.IntegerField()
    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reg_id')
    reg_date = models.DateTimeField()
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='mod_id')
    mod_date = models.DateTimeField()
    order = models.PositiveIntegerField(default=0, db_index=True)
    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="modules",
        db_index=True,
    )

    def save(self, *args, **kwargs):
        # 신규 등록이거나 sort_order가 0이면 맨 뒤로 붙이기
        if not self.order:
            from django.db.models import Max
            max_order = (
                Module.objects.filter(branch=self.branch).aggregate(m=Max('order'))['m'] or 0
            )
            self.order = max_order + 1
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["branch", "order"], name="module_branch_order_idx"),
        ]


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
    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="contracts",
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["branch", "user_id", "stand_date"], name="contract_branch_user_date_idx"),
        ]


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
    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="schedules",
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["branch", "year", "month", "user_id"], name="schedule_branch_ym_user_idx"),
        ]


# 근태기록
class Work(models.Model):
    class WorkCode(models.TextChoices):
        IN = 'I', '출근'
        OUT = 'O', '퇴근'

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    work_code = models.CharField(max_length=1, choices=WorkCode.choices, verbose_name="근로코드")
    record_date = models.DateTimeField()
    record_day = models.DateField(editable=False, null=False, blank=False, db_index=True)
    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="works",
        db_index=True,
    )

    class Meta:
        permissions = [
            ("bypass_beacon", "비콘 바이패스 권한"),
        ]
        indexes = [
            models.Index(fields=["branch", "record_day"], name="work_branch_day_idx"),
            models.Index(fields=["branch", "user_id", "record_day"], name="work_branch_user_day_idx"),
        ]

# Work 저장시 항상 record_day를 record_date에 맞춰 설정해줌
@receiver(pre_save, sender=Work)
def set_record_day(sender, instance: Work, **kwargs):
    # record_date 안 채웠으면 now() 사용 (앱에서 즉시 입력시) cf) 웹에서는 근태시간을 자유롭게 명시해서 입력 가능
    if not instance.record_date:
        instance.record_date = timezone.now()
    # 항상 record_day 동기화
    instance.record_day = instance.record_date.date()


# 비콘정보
class Beacon(models.Model):
    branch = models.ForeignKey(Branch, verbose_name="지점", on_delete=models.PROTECT, related_name="beacons")
    name = models.CharField("비콘명", max_length=100)  # 예: "1층 카운터 앞"

    uuid = models.CharField(max_length=64)
    major = models.IntegerField()
    minor = models.IntegerField()

    # 거리/신호 튜닝용
    max_distance_meters = models.FloatField("최대 인식 거리(m)", default=3.0)
    rssi_threshold = models.IntegerField("RSSI 임계값(dBm)", default=-65)
    tx_power = models.IntegerField("Tx Power", default=-59)  # 선택

    stabilize_count = models.IntegerField("연속 인식 횟수", default=3)
    timeout_seconds = models.IntegerField("시간초과(초)", default=10)

    is_active = models.BooleanField("사용여부", default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    memo = models.TextField("비고", blank=True)

    reg_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='beacon_reg_id')
    reg_date = models.DateTimeField(auto_now_add=True)
    mod_id = models.ForeignKey(User, on_delete=models.PROTECT, related_name='beacon_mod_id')
    mod_date = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("branch", "uuid", "major", "minor")

    def __str__(self):
        return f"{self.branch.name} - {self.name} ({self.major}/{self.minor})"


class BranchMonthClose(models.Model):
    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="month_closes",
        db_index=True,
    )
    ym = models.CharField("마감월", max_length=6)
    is_closed = models.BooleanField("마감여부", default=False)
    closed_at = models.DateTimeField("마감일시", null=True, blank=True)
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="month_closes_closed_by",
    )
    snapshot_json = models.JSONField(null=True, blank=True)
    reg_date = models.DateTimeField(auto_now_add=True)
    mod_date = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("branch", "ym")
        indexes = [
            models.Index(fields=["branch", "ym"], name="branch_month_close_idx"),
        ]


class MealClaim(models.Model):
    SOURCE_TYPE_CHOICES = [
        ("MANUAL", "MANUAL"),
    ]

    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="meal_claims",
        db_index=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="meal_claims",
        db_index=True,
    )
    used_date = models.DateField("사용일", db_index=True)
    amount = models.IntegerField("금액")
    approval_no = models.CharField("승인번호", max_length=64, default="")
    merchant_name = models.CharField("가맹점명", max_length=120, default="")
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default="MANUAL",
    )
    is_deleted = models.BooleanField(default=False)
    reg_date = models.DateTimeField(auto_now_add=True)
    mod_date = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["branch", "used_date"], name="meal_claim_branch_date_idx"),
            models.Index(fields=["user", "used_date"], name="meal_claim_user_date_idx"),
            models.Index(fields=["branch", "approval_no"], name="meal_claim_branch_approval_idx"),
        ]


class MealClaimParticipant(models.Model):
    claim = models.ForeignKey(
        MealClaim,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="meal_claim_participants")
    amount = models.IntegerField("분배금액")

    class Meta:
        unique_together = ("claim", "user")
