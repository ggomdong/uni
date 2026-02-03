from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from ..models import Question


@login_required(login_url='common:login')
def index(request):
    branch = request.branch
    page = request.GET.get('page', '1')     # 페이지 default 값은 1
    kw = request.GET.get('kw', '')      # 검색어
    question_list = Question.objects.filter(branch=branch).order_by('-create_date')
    if kw:
        question_list = question_list.filter(       # icontains 는 대소문자 구별하지 않음 (contains는 구별)
            Q(subject__icontains=kw) |      # 제목 검색
            Q(content__icontains=kw) |      # 내용 검색
            Q(answer__content__icontains=kw) |    # 답변 내용 검색
            Q(author__username__icontains=kw) |   # 질문 글쓴이 검색
            Q(answer__author__username__icontains=kw)   # 답변 글쓴이 검색
        ).distinct()

    paginator = Paginator(question_list, 10)    # 페이지당 10개씩 보여주기
    page_obj = paginator.get_page(page)     # 해당 페이지의 데이터만 조회
    context = {'question_list': page_obj, 'page': page, 'kw': kw}
    return render(request, 'pybo/question_list.html', context)


@login_required(login_url='common:login')
def detail(request, question_id):
    branch = request.branch
    question = get_object_or_404(Question, pk=question_id, branch=branch)
    context = {'question': question}
    return render(request, 'pybo/question_detail.html', context)
