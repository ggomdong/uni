from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from django.contrib.auth.models import User
from .models import User, Dept, Position, Holiday, Business, Code

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


class PasswordChangeForm(forms.Form):
    new_password = forms.CharField(
        label="새 비밀번호", widget=forms.PasswordInput,
        min_length=8, help_text="8자 이상 입력하세요."
    )
    confirm_password = forms.CharField(
        label="비밀번호 확인", widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get("new_password")
        pw2 = cleaned_data.get("confirm_password")
        if pw1 != pw2:
            raise forms.ValidationError("비밀번호가 일치하지 않습니다.")
        return cleaned_data


class DeptForm(forms.ModelForm):
    class Meta:
        model = Dept
        fields = ['dept_name', 'order']

        labels = {
            'dept_name': '부서명',
            'order': '출력순서',
        }

        widgets = {
            'dept_name': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['position_name', 'order']

        labels = {
            'position_name': '직위명',
            'order': '출력순서',
        }

        widgets = {
            'position_name': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.TextInput(attrs={'class': 'form-control'}),
        }


class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = ['holiday', 'holiday_name']

        labels = {
            'holiday': '공휴일',
            'holiday_name': '공휴일명',
        }

        widgets = {
            'holiday': forms.DateInput(attrs={'type': 'date', 'max': '9999-12-31', 'class': 'form-control'}),
            'holiday_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['stand_date', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        labels = {
            'stand_date': '기준일자',
            'mon': '월요일',
            'tue': '화요일',
            'wed': '수요일',
            'thu': '목요일',
            'fri': '금요일',
            'sat': '토요일',
            'sun': '일요일',
        }

        CHOICES = [
            ('Y', '영업'),
            ('N', '미영업'),
        ]

        widgets = {
            'stand_date': forms.DateInput(attrs={'type': 'date', 'max': '9999-12-31', 'class': 'form-control'}),
            'mon': forms.RadioSelect(choices=CHOICES),
            'tue': forms.RadioSelect(choices=CHOICES),
            'wed': forms.RadioSelect(choices=CHOICES),
            'thu': forms.RadioSelect(choices=CHOICES),
            'fri': forms.RadioSelect(choices=CHOICES),
            'sat': forms.RadioSelect(choices=CHOICES),
            'sun': forms.RadioSelect(choices=CHOICES),
        }


class CodeForm(forms.ModelForm):
    class Meta:
        model = Code
        fields = ['code_name', 'value', 'order']

        labels = {
            'code_name': '코드명',
            'value': '코드값',
            'order': '출력순서',
        }

        widgets = {
            'code_name': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.TextInput(attrs={'class': 'form-control'}),
        }
