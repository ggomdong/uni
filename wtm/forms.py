from django import forms
from .models import Module, Contract, Schedule


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['cat', 'name', 'start_time', 'end_time', 'rest1_start_time', 'rest1_end_time',
                  'rest2_start_time', 'rest2_end_time', 'color']

        labels = {
            'cat': '구분',
            'name': '근무명',
            'start_time': '근무시간(시업)',
            'end_time': '근무시간(종업)',
            'rest1_start_time': '휴게시간1(시작)',
            'rest1_end_time': '휴게시간1(종료)',
            'rest2_start_time': '휴게시간2(시작)',
            'rest2_end_time': '휴게시간2(종료)',
            'color': '색상',
        }


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ['stand_date', 'type', 'check_yn', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        labels = {
            'stand_date': '기준일자',
            'type': '근무형태',
            'check_yn': '근태확인',
            'mon': '월요일',
            'tue': '화요일',
            'wed': '수요일',
            'thu': '목요일',
            'fri': '금요일',
            'sat': '토요일',
            'sun': '일요일',
        }


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['user', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'd10',
                  'd11', 'd12', 'd13', 'd14', 'd15', 'd16', 'd17', 'd18', 'd19', 'd20', 'd21', 'd22',
                  'd23', 'd24', 'd25', 'd26', 'd27', 'd28', 'd29', 'd30', 'd31']

        # widgets = {'d1': forms.TextInput(attrs={'class': 'module_box'})},
