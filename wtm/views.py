from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from common.models import User
from .models import Work


@login_required(login_url='common:login')
def work_list(request):
    page = request.GET.get('page', '1')     # 페이지 default 값은 1
    kw = request.GET.get('kw', '')      # 검색어
    query_set = Work.objects.all()
    if kw:
        query_set = query_set.filter(       # icontains 는 대소문자 구별하지 않음 (contains는 구별)
            Q(username__icontains=kw) |     # ID 검색
            Q(emp_name__icontains=kw) |     # 직원명 검색
            Q(dept__icontains=kw) |         # 부서명 검색
            Q(position__icontains=kw) |     # 직위명 검색
            Q(email__icontains=kw)          # 이메일 검색
        ).distinct()

    paginator = Paginator(query_set, 10)    # 페이지당 10개씩 보여주기
    page_obj = paginator.get_page(page)     # 해당 페이지의 데이터만 조회
    context = {'work_list': page_obj, 'page': page, 'kw': kw}
    return render(request, 'wtm/work_list.html', context)
