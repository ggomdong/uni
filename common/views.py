from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .forms import UserForm, UserModifyForm
from .models import User


def page_not_found(request, exception):
    return render(request, 'common/404.html', {})

@login_required(login_url='common:login')
def signup(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            # form.cleaned_data.get 은 폼의 입력값을 개별적으로 획득하고 싶을때 사용
            # username = form.cleaned_data.get('username')
            # raw_password = form.cleaned_data.get('password1')
            # user = authenticate(username=username, password=raw_password)   # 사용자 인증
            # login(request, user)    # 로그인 처리
            return redirect('common:user_list')
    else:
        form = UserForm()
    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'form': form}
    return render(request, 'common/signup.html', context)


@login_required(login_url='common:login')
def user_list(request):
    page = request.GET.get('page', '1')     # 페이지 default 값은 1
    kw = request.GET.get('kw', '')      # 검색어
    query_set = User.objects.order_by('date_joined').exclude(username='admin')
    if kw:
        query_set = query_set.filter(       # icontains 는 대소문자 구별하지 않음 (contains는 구별)
            Q(username__icontains=kw) |     # ID 검색
            Q(emp_name__icontains=kw) |     # 직원명 검색
            Q(dept__icontains=kw) |         # 부서명 검색
            Q(position__icontains=kw) |     # 직위명 검색
            Q(email__icontains=kw)          # 이메일 검색
        ).distinct()

    paginator = Paginator(query_set, 100)    # 페이지당 10개씩 보여주기
    page_obj = paginator.get_page(page)     # 해당 페이지의 데이터만 조회
    context = {'user_list': page_obj, 'page': page, 'kw': kw}
    return render(request, 'common/user_list.html', context)


@login_required(login_url='common:login')
def user_modify(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        # 수정된 내용을 반영하기 위해, request에서 넘어온 값으로 덮어쓰라는 의미
        form = UserModifyForm(request.POST, instance=user)
        # 수정 사항이 없을 경우 에러 발생
        if not form.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:user_modify', user_id=user_id)

        if form.is_valid():
            user.save()
            return redirect('common:user_list')
    # 수정 버튼 클릭시 GET 방식으로 수정화면 호출
    else:
        # 내용이 유지되어야 하므로, instance=user 와 같이 생성
        form = UserModifyForm(instance=user)
        context = {'form': form}
        return render(request, 'common/user_modify.html', context)