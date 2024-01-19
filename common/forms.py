from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from django.contrib.auth.models import User
from .models import User

# 속성 추가를 위해 UserCreationForm 사용
class UserForm(UserCreationForm):
    email = forms.EmailField(label="이메일")

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "emp_name", "email", "dept", "position", "join_date", "out_date")

        labels = {
            'username': 'ID',
            'password1': '비밀번호',
            'password2': '비밀번호 확인',
            'emp_name': '직원명',
            'email': '이메일',
            'dept': '부서명',
            'position': '직위명',
            'join_date': '입사일자',
            'out_date': '퇴사일자',
        }


class UserModifyForm(UserChangeForm):
    username = forms.CharField(disabled=True)

    class Meta:
        model = User
        fields = ("username", "emp_name", "email", "dept", "position", "join_date", "out_date")

        labels = {
            'username': 'ID',
            'emp_name': '직원명',
            'email': '이메일',
            'dept': '부서명',
            'position': '직위명',
            'join_date': '입사일자',
            'out_date': '퇴사일자',
        }
