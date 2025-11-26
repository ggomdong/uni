from django.contrib import admin
from django.utils import timezone
from .models import Module, Contract, Schedule, Work, Beacon


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cat",
        "name",
        "start_time",
        "end_time",
        "rest1_start_time",
        "rest1_end_time",
        "rest2_start_time",
        "rest2_end_time",
        "color",
        "reg_id",
        "reg_date",
        "mod_id",
        "mod_date",
    )
    list_filter = ("cat",)
    search_fields = ("cat", "name")
    ordering = ("cat", "name")

    # reg/mod는 폼에서 숨기고 날짜는 읽기전용
    exclude = ("reg_id", "mod_id")
    readonly_fields = ("reg_date", "mod_date")

    def save_model(self, request, obj, form, change):
        now = timezone.now()
        if not change or not obj.reg_id_id:
            obj.reg_id = request.user
            if not obj.reg_date:
                obj.reg_date = now
        obj.mod_id = request.user
        obj.mod_date = now
        super().save_model(request, obj, form, change)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "stand_date",
        "type",
        "check_yn",
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
        "reg_id",
        "reg_date",
        "mod_id",
        "mod_date",
    )
    list_filter = ("type", "check_yn", "stand_date")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    date_hierarchy = "stand_date"
    ordering = ("-stand_date", "user")

    exclude = ("reg_id", "mod_id")
    readonly_fields = ("reg_date", "mod_date")

    # 유저/모듈이 많으니 select 대신 검색 팝업으로
    raw_id_fields = (
        "user",
        "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    )

    def save_model(self, request, obj, form, change):
        now = timezone.now()
        if not change or not obj.reg_id_id:
            obj.reg_id = request.user
            if not obj.reg_date:
                obj.reg_date = now
        obj.mod_id = request.user
        obj.mod_date = now
        super().save_model(request, obj, form, change)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "year",
        "month",
        "reg_id",
        "reg_date",
        "mod_id",
        "mod_date",
    )
    list_filter = ("year", "month")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    ordering = ("-year", "-month", "user")

    exclude = ("reg_id", "mod_id")
    readonly_fields = ("reg_date", "mod_date")

    # 모듈/유저가 많으니 raw_id로
    raw_id_fields = (
        "user",
        "d1", "d2", "d3", "d4", "d5", "d6", "d7",
        "d8", "d9", "d10", "d11", "d12", "d13", "d14",
        "d15", "d16", "d17", "d18", "d19", "d20", "d21",
        "d22", "d23", "d24", "d25", "d26", "d27", "d28",
        "d29", "d30", "d31",
    )

    def save_model(self, request, obj, form, change):
        now = timezone.now()
        if not change or not obj.reg_id_id:
            obj.reg_id = request.user
            if not obj.reg_date:
                obj.reg_date = now
        obj.mod_id = request.user
        obj.mod_date = now
        super().save_model(request, obj, form, change)


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "work_code",
        "record_day",
        "record_date",
    )
    list_filter = ("work_code", "record_day")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    date_hierarchy = "record_day"
    ordering = ("-record_day", "-record_date")

    raw_id_fields = ("user",)


@admin.register(Beacon)
class BeaconAdmin(admin.ModelAdmin):
    list_display = (
        "branch",
        "name",
        "uuid",
        "major",
        "minor",
        "max_distance_meters",
        "rssi_threshold",
        "is_active",
        "reg_id",
        "reg_date",
        "mod_id",
        "mod_date",
    )
    list_filter = ("branch", "is_active")
    search_fields = ("name", "uuid", "major", "minor")
    ordering = ("branch", "name")

    # reg_id / mod_id 는 화면에서 안 보이게, 날짜는 읽기전용
    exclude = ("reg_id", "mod_id")
    readonly_fields = ("reg_date", "mod_date")

    def save_model(self, request, obj, form, change):
        """
        admin에서 저장할 때 reg_id / mod_id 자동 세팅
        """
        if not change or not obj.reg_id_id:
            obj.reg_id = request.user
        obj.mod_id = request.user
        super().save_model(request, obj, form, change)