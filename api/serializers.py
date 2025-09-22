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


# serializers.py
class AttendanceDaySerializer(serializers.Serializer):
    record_day = serializers.DateField()
    work_start = serializers.CharField(allow_null=True)
    work_end = serializers.CharField(allow_null=True)
    checkin_time = serializers.CharField(allow_null=True)  # HH:mm or null
    checkout_time = serializers.CharField(allow_null=True)  # HH:mm or null
    work_cat = serializers.CharField(allow_null=True)  # 근무 대분류
    work_name = serializers.CharField(allow_null=True)  # 근무 세부명
    work_color_code = serializers.IntegerField(allow_null=True)  # DB의 정수값
    work_color_hex = serializers.CharField(allow_null=True)       # 매핑된 HEX
    is_late = serializers.BooleanField()
    is_early_checkout = serializers.BooleanField()
    is_overtime = serializers.BooleanField()


class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['user', 'work_code', 'record_date']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'emp_name', 'dept', 'position', 'email', 'join_date', 'out_date']