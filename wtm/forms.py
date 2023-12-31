from django import forms
from .models import Module


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
