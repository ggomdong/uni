from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import connection
from django.forms import modelformset_factory
from .forms import UserForm, UserModifyForm, DeptForm, PositionForm, CodeForm
from .models import User, Dept, Position, Code
from wtm.models import Module, Contract
from django.utils import timezone


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

            # 직원 등록 후 바로 근로계약을 입력할 수 있도록 수정화면으로 이동.
            # 이를 위해 지금 등록한 user의 id를 얻어야 하므로, 가장 최근 유저의 id를 가져옴.
            user = User.objects.last()
            return redirect('wtm:work_contract_reg', user_id=user.id)
    else:
        form = UserForm()

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    dept_list = list(Dept.objects.values_list('dept_name', flat=True).order_by('order'))
    position_list = list(Position.objects.values_list('position_name', flat=True).order_by('order'))
    context = {'form': form, 'dept_list': dept_list, 'position_list': position_list}
    return render(request, 'common/signup.html', context)


@login_required(login_url='common:login')
def user_list(request):
    order_by = request.GET.get('order_by', 'do, po, join_date')
    search_work = request.GET.get('work', '재직자')
    search_dept = request.GET.get('dept', '전체')
    search_position = request.GET.get('position', '전체')

    match search_work:
        case '전체':
            work_condition = '1=1'
        case '퇴사자':
            work_condition = 'out_date is not null'
        case _:
            work_condition = 'out_date is null'

    match search_dept:
        case '전체':
            dept_condition = '1=1'
        case _:
            dept_condition = 'dept = "{}"'.format(search_dept)

    match search_position:
        case '전체':
            position_condition = '1=1'""
        case _:
            position_condition = 'position = "{}"'.format(search_position)

    # User를 메인으로 Contract를 LEFT OUTER JOIN 하여, 계약이 있는 경우에만 리스트에 보여줌
    # 1. 현재(NOW())보다 과거인 기준일이 존재하면 max(과거 기준일)
    # 2. 현재(NOW())보다 과거인 기준일이 없으면 min(미래 기준일)
    # SQL에 조건을 넣기가 애매해서, 1,2를 union한 후 min 값을 얻는 걸로 구현함
    raw_query = f'''
        SELECT u.id, u.emp_name, u.dept, u.position, u.join_date, u.out_date,
                c.id as cid, c.stand_date, c.type, c.check_yn, c.mon_id as mon, c.tue_id as tue, c.wed_id as wed,
                c.thu_id as thu, c.fri_id as fri, c.sat_id as sat, c.sun_id as sun,
                d.order as do, p.order as po
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
            INNER JOIN common_dept d on (u.dept = d.dept_name)
			INNER JOIN common_position p on (u.position = p.position_name)
        WHERE is_superuser = false 
            and {work_condition}
            and {dept_condition}
            and {position_condition}
        ORDER BY {order_by}
        '''

    #print(raw_query)

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

    #print(query_set)

    dept_list = list(Dept.objects.values_list('dept_name', flat=True).order_by('order'))
    position_list = list(Position.objects.values_list('position_name', flat=True).order_by('order'))

    module_list = Module.objects.all()
    context = {'user_list': query_set, 'dept_list': dept_list, 'position_list': position_list,
               'module_list': module_list,
               'search_work': search_work, 'search_dept': search_dept, 'search_position': search_position}
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
    dept_list = list(Dept.objects.values_list('dept_name', flat=True).order_by('order'))
    position_list = list(Position.objects.values_list('position_name', flat=True).order_by('order'))
    module_list = Module.objects.all()
    contract_list = Contract.objects.filter(user_id=user_id).order_by('-stand_date')
    context = {'form': form, 'dept_list': dept_list, 'position_list': position_list,
               'module_list': module_list, 'contract_list': contract_list, 'user_id': user_id}
    return render(request, 'common/user_modify.html', context)


@login_required(login_url='common:login')
def dept_list(request):
    DeptFormSet = modelformset_factory(model=Dept, form=DeptForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = DeptFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:dept_list')

        if formset.is_valid():
            depts = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for dept in depts:
                dept.reg_id = request.user
                dept.reg_date = timezone.now()
                dept.mod_id = request.user
                dept.mod_date = timezone.now()
                dept.save()

            return redirect('common:dept_list')
    else:
        formset = DeptFormSet()

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'formset': formset}
    return render(request, 'common/dept_list.html', context)


@login_required(login_url='common:login')
def position_list(request):
    PositionFormSet = modelformset_factory(model=Position, form=PositionForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = PositionFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:position_list')

        if formset.is_valid():
            positions = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for position in positions:
                position.reg_id = request.user
                position.reg_date = timezone.now()
                position.mod_id = request.user
                position.mod_date = timezone.now()
                position.save()

            return redirect('common:position_list')
    else:
        formset = PositionFormSet()

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'formset': formset}
    return render(request, 'common/position_list.html', context)


@login_required(login_url='common:login')
def code_list(request):
    search = request.GET.get('search', '전체')

    CodeFormSet = modelformset_factory(model=Code, form=CodeForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = CodeFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:code_list')

        if formset.is_valid():
            codes = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for code in codes:
                code.reg_id = request.user
                code.reg_date = timezone.now()
                code.mod_id = request.user
                code.mod_date = timezone.now()
                code.save()

            return redirect('common:code_list')
    else:
        if search == '전체':
            qs = CodeFormSet(queryset=Code.objects.order_by('code_name', 'order'))
        else:
            qs = CodeFormSet(queryset=Code.objects.order_by('code_name', 'order').filter(code_name=search))

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    # 코드명 검색을 위해 QuerySet을 해당값만으로 리스트 구성(flat)하고, 중복제거(distinct)
    formset = qs
    code_name_list = list(Code.objects.values_list('code_name', flat=True).distinct())  # [부서, 직위]
    context = {'formset': formset, 'code_name_list': code_name_list, 'search': search}
    return render(request, 'common/code_list.html', context)
