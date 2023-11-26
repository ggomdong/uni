from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from ..forms import QuestionForm
from ..models import Question


@login_required(login_url='common:login')
def question_create(request):
    if request.method == 'POST':    # 폼에서 submit 눌렀을때는 POST로 요청됨
        form = QuestionForm(request.POST)       # request.POST에는 사용자가 입력한 subject, content 값이 담겨있음
        if form.is_valid():     # 폼이 유효하다면(즉, subject, content 값이 올바르다면). 아니면 폼에는 오류메시지가 저장됨
            # 아직 create_date 값이 없어서 바로 저장하면 오류가 남.임시 저장하여 question 객체를 받음
            question = form.save(commit=False)
            question.author = request.user
            question.create_date = timezone.now()   # 실제 저장을 위해 작성일시 설정
            question.save()     # 실제로 저장
            return redirect('pybo:index')
    else:   # "질문 등록" 버튼을 눌러서 'pybo:question_create'를 호출하면 GET 방식이므로 질문 등록 화면을 보여줌
        form = QuestionForm()

    context = {'form': form}
    return render(request, 'pybo/question_form.html', context)


@login_required(login_url='common:login')
def question_modify(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    if request.user != question.author:
        messages.error(request, '수정권한이 없습니다.')
        return redirect('pybo:detail', question_id=question_id)
    # 질문 수정화면에서 저장하기 버튼 클릭시 POST 방식으로 데이터 수정
    if request.method == 'POST':
        # 수정된 내용을 반영하기 위해, request에서 넘어온 값으로 덮어쓰라는 의미
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save(commit=False)
            question.modify_date = timezone.now()
            question.save()
            return redirect('pybo:detail', question_id=question.id)
    # 질문 수정 버튼 클릭시 GET 방식으로 수정화면 호출
    else:
        # 질문의 제목/내용이 유지되어야 하므로, instance=question 과 같이 생성
        form = QuestionForm(instance=question)

    context = {'form': form}
    return render(request, 'pybo/question_form.html', context)


@login_required(login_url='common:login')
def question_delete(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    if request.user != question.author:
        messages.error(request, '삭제 권한이 없습니다.')
        return redirect('pybo:detail', question_id=question.id)
    question.delete()
    return redirect('pybo:index')


@login_required(login_url='common:login')
def question_vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    if request.user == question.author:
        messages.error(request, '본인이 작성한 글은 추천할 수 없습니다.')
    # 이미 추천한 경우, 다시 누르면 추천을 제거함
    elif request.user == question.voter.filter(username=request.user).first():
        question.voter.remove(request.user)
    # 추천
    else:
        question.voter.add(request.user)
    return redirect('pybo:detail', question_id=question.id)
