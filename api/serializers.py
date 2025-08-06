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


class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['user', 'work_code', 'record_date']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'emp_name', 'dept', 'position', 'email', 'join_date', 'out_date']