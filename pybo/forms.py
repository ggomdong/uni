from django import forms
from .models import Question, Answer


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question    # 사용할 모델
        fields = ['subject', 'content']     # QuestionForm에서 사용할 Question 모델의 속성

        # 아래 내용은 form.as_p로 자동 생성시 필요한 부분임
        # # {{ form.as_p }} 태그는 HTML 코드를 자동으로 생성하기 때문에 Bootstrap 적용이 불가
        # # 따라서, Bootstrap 사용을 위한 방법으로 widget 추가
        # widgets = {
        #     'subject': forms.TextInput(attrs={'class': 'form-control'}),
        #     'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
        # }
        # fields는 모델을 그대로 가져오기 때문에 영문으로 표시됨. 한글로 변경하기 위해 label 지정
        labels = {
            'subject': '제목',
            'content': '내용',
        }

class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['content']
        labels = {
            'content': '내용',
        }