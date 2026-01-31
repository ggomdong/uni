from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect, resolve_url
from django.utils import timezone

from ..forms import AnswerForm
from ..models import Question, Answer


@login_required(login_url='common:login')
def answer_create(request, question_id):
    question = get_object_or_404(Question, pk=question_id, branch=request.user.branch)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.author = request.user
            answer.question = question
            answer.create_date = timezone.now()
            answer.branch = question.branch
            answer.save()
            # return redirect('pybo:detail', question_id=question.id)
            return redirect('{}#answer_{}'.format(
                resolve_url('pybo:detail', question_id=question.id), answer.id))
    else:
        form = AnswerForm()

    context = {'question': question, 'form': form}
    return render(request, 'pybo/question_detail.html', context)


@login_required(login_url='common:login')
def answer_modify(request, answer_id):
    answer = get_object_or_404(Answer, pk=answer_id, branch=request.user.branch)
    if request.user != answer.author:
        messages.error(request, '수정권한이 없습니다.')
        # return redirect('pybo:detail', question_id=answer.question.id)
        return redirect('{}#answer_{}'.format(
            resolve_url('pybo:detail', question_id=answer.question.id), answer.id))
    # 수정화면에서 저장하기 버튼 클릭시 POST 방식으로 데이터 수정
    if request.method == 'POST':
        # 수정된 내용을 반영하기 위해, request에서 넘어온 값으로 덮어쓰라는 의미
        form = AnswerForm(request.POST, instance=answer)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.modify_date = timezone.now()
            answer.save()
            # return redirect('pybo:detail', question_id=answer.question.id)
            return redirect('{}#answer_{}'.format(
                resolve_url('pybo:detail', question_id=answer.question.id), answer.id))
    # 질문 수정 버튼 클릭시 GET 방식으로 수정화면 호출
    else:
        # 질문의 제목/내용이 유지되어야 하므로, instance=question 과 같이 생성
        form = AnswerForm(instance=answer)

    context = {'answer': answer, 'form': form}
    return render(request, 'pybo/answer_form.html', context)


@login_required(login_url='common:login')
def answer_delete(request, answer_id):
    answer = get_object_or_404(Answer, pk=answer_id, branch=request.user.branch)
    if request.user != answer.author:
        messages.error(request, '삭제 권한이 없습니다.')
    else:
        answer.delete()
    # return redirect('pybo:detail', question_id=answer.question.id)
    return redirect('{}#answer_{}'.format(
        resolve_url('pybo:detail', question_id=answer.question.id), answer.id))


@login_required(login_url='common:login')
def answer_vote(request, answer_id):
    answer = get_object_or_404(Answer, pk=answer_id, branch=request.user.branch)
    if request.user == answer.author:
        messages.error(request, '본인이 작성한 답변은 추천할 수 없습니다.')
    # 이미 추천한 경우, 다시 누르면 추천을 제거함
    elif request.user == answer.voter.filter(username=request.user).first():
        answer.voter.remove(request.user)
    # 추천
    else:
        answer.voter.add(request.user)
    return redirect('pybo:detail', question_id=answer.question.id)
