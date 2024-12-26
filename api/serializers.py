from rest_framework import serializers
from common.models import User
from wtm.models import Work


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'emp_name', 'dept', 'position', 'email', 'join_date', 'out_date']


class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['user', 'work_code', 'record_date']
