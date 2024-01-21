from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import UserForm, UserModifyForm
from .models import User
from wtm.models import Module, Contract
from django.db import connection


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
    order_by = request.GET.get('order_by', 'join_date')
    work = request.GET.get('work', '재직자')
    page = request.GET.get('page', '1')     # 페이지 default 값은 1
    #query_set = User.objects.order_by('date_joined').exclude(username='admin')

    print(work)
    match work:
        case '전체':
            work_condition = '1=1'
        case '퇴사자':
            work_condition = 'out_date is not null'
        case _:
            work_condition = 'out_date is null'

    # User를 메인으로 Contract를 LEFT OUTER JOIN 하여, 계약이 있는 경우에만 리스트에 보여줌
    # 1. 현재(NOW())보다 과거인 기준일이 존재하면 max(과거 기준일)
    # 2. 현재(NOW())보다 과거인 기준일이 없으면 min(미래 기준일)
    # SQL에 조건을 넣기가 애매해서, 1,2를 union한 후 min 값을 얻는 걸로 구현함
    raw_query = '''
        SELECT u.id, u.emp_name, u.dept, u.position, u.join_date, u.out_date,
                c.stand_date, c.type, c.check_yn, c.mon_id as mon, c.tue_id as tue, c.wed_id as wed,
                c.thu_id as thu, c.fri_id as fri, c.sat_id as sat, c.sun_id as sun
        FROM common_user u LEFT OUTER JOIN (SELECT * FROM wtm_contract WHERE (user_id, stand_date) in
            (
                SELECT a.user_id, min(a.stand_date)
                FROM 
                (
                    SELECT user_id, max(stand_date) as stand_date FROM wtm_contract WHERE stand_date <= NOW() GROUP BY user_id
                    UNION
                    SELECT user_id, min(stand_date) as stand_date FROM wtm_contract WHERE stand_date > NOW() GROUP BY user_id
                    ) a
                    group by a.user_id
                ) 
            ) c
            ON (u.id = c.user_id)
        WHERE is_superuser = false and {work_condition}
        ORDER BY {order_by}
        '''.format(work_condition=work_condition, order_by=order_by)

    print(raw_query)

    with connection.cursor() as cursor:
        cursor.execute(raw_query)
        results = cursor.fetchall()

        x = cursor.description
        query_set = []
        for r in results:
            i = 0
            d = {}
            while i < len(x):
                d[x[i][0]] = r[i]
                i = i + 1
            query_set.append(d)

    print(query_set)

    paginator = Paginator(query_set, 100)    # 페이지당 10개씩 보여주기
    page_obj = paginator.get_page(page)     # 해당 페이지의 데이터만 조회

    module_list = Module.objects.all()
    context = {'user_list': page_obj, 'module_list': module_list, 'page': page, 'work': work}
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

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    module_list = Module.objects.all()
    contract_list = Contract.objects.filter(user_id=user_id).order_by('-stand_date')
    context = {'form': form, 'module_list': module_list, 'contract_list': contract_list, 'user_id': user_id}
    return render(request, 'common/user_modify.html', context)