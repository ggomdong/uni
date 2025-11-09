from rest_framework import serializers
from common.models import User
from wtm.models import Work


class AttendanceSerializer(serializers.Serializer):
    emp_name = serializers.CharField()
    work_start = serializers.CharField(allow_null=True)
    work_end = serializers.CharField(allow_null=True)
    checkin_time = serializers.DateTimeField(allow_null=True)
    checkout_time = serializers.DateTimeField(allow_null=True)
    is_early_checkout = serializers.BooleanField()


class MonthlyAttendanceDaySerializer(serializers.Serializer):
    record_day = serializers.DateField()

    work_start = serializers.CharField(allow_null=True)
    work_end = serializers.CharField(allow_null=True)
    checkin_time = serializers.CharField(allow_null=True)   # "HH:mm:ss" or null
    checkout_time = serializers.CharField(allow_null=True)  # "HH:mm:ss" or null

    # (하위호환) 조합 문자열은 남겨두되, 앱에선 안 써도 됨
    status = serializers.CharField()

    # 상태 코드 리스트
    status_codes = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )

    # 상태 라벨 리스트
    status_labels = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )

    # 모듈(스케줄) 정보
    work_cat = serializers.CharField(allow_null=True)
    work_name = serializers.CharField(allow_null=True)
    work_color_code = serializers.IntegerField(allow_null=True)
    work_color_hex = serializers.CharField(allow_null=True)

    # 분 단위 지표
    late_seconds = serializers.IntegerField()
    early_seconds = serializers.IntegerField()
    overtime_seconds = serializers.IntegerField()
    holiday_seconds = serializers.IntegerField()

    # 편의 boolean
    is_late = serializers.BooleanField()
    is_early_checkout = serializers.BooleanField()
    is_overtime = serializers.BooleanField()


class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['user', 'work_code', 'record_date']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'emp_name', 'dept', 'position', 'email', 'join_date', 'out_date']