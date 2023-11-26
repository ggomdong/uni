from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from django.contrib.auth.models import User
from .models import User

# 속성 추가를 위해 UserCreationForm 사용
class UserForm(UserCreationForm):
    email = forms.EmailField(label="이메일")

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "email", "emp_name", "dept", "position", "join_date", "out_date")


class UserModifyForm(UserChangeForm):
    username = forms.CharField(disabled=True)

    class Meta:
        model = User
        fields = ("username", "email", "emp_name", "dept", "position", "join_date", "out_date")
