from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import ExtractYear
from django.db import connection
from django.forms import modelformset_factory
from .forms import UserForm, UserModifyForm, DeptForm, PositionForm, HolidayForm, BusinessForm, CodeForm
from .models import User, Dept, Position, Holiday, Business, Code
from wtm.models import Module, Contract
from django.utils import timezone
from datetime import datetime


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
    order = request.GET.get('order', '0')
    search_work = request.GET.get('work', '재직자')
    search_dept = request.GET.get('dept', '전체')
    search_position = request.GET.get('position', '전체')

    # 0~5는 오름차순, 뒤에 1이 붙으면 내림차순
    match order[0]:
        case '0':
            order_condition = 'do asc, po, join_date'
        case '1':
            order_condition = 'emp_name asc, do, po, join_date'
        case '2':
            order_condition = 'join_date asc, do, po'
        case '3':
            order_condition = 'out_date asc, do, po, join_date'
        case _:
            order_condition = 'do, po, join_date'

    if len(order) == 2:
        order_condition = order_condition.replace('asc', 'desc')

    stand_ym = datetime.today().strftime('%Y%m')

    match search_work:
        case '전체':
            work_condition = '1=1'
        case '퇴사자':
            work_condition = f'DATE_FORMAT(u.out_date, "%Y%m") < "{stand_ym}"'
        case _:
            work_condition = f'(out_date is null or DATE_FORMAT(u.out_date, "%Y%m") >= "{stand_ym}")'

    match search_dept:
        case '전체':
            dept_condition = '1=1'
        case _:
            dept_condition = f'dept = "{search_dept}"'

    match search_position:
        case '전체':
            position_condition = '1=1'
        case _:
            position_condition = f'position = "{search_position}"'

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
            LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name)
			LEFT OUTER JOIN common_position p on (u.position = p.position_name)
        WHERE is_superuser = false 
            and {work_condition}
            and {dept_condition}
            and {position_condition}
        ORDER BY {order_condition}
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
               'module_list': module_list, 'order': order,
               'search_work': search_work, 'search_dept': search_dept, 'search_position': search_position}
    return render(request, 'common/user_list.html', context)


@login_required(login_url='common:login')
def nametag(request, emp_name, position):
    context = {'emp_name': emp_name, 'position': position}
    return render(request, 'common/nametag.html', context)


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
def dept(request):
    DeptFormSet = modelformset_factory(model=Dept, form=DeptForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = DeptFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:dept')

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

            return redirect('common:dept')
    else:
        formset = DeptFormSet(queryset=Dept.objects.order_by('order'))

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'formset': formset}
    return render(request, 'common/dept.html', context)


@login_required(login_url='common:login')
def position(request):
    PositionFormSet = modelformset_factory(model=Position, form=PositionForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = PositionFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:position')

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

            return redirect('common:position')
    else:
        formset = PositionFormSet(queryset=Position.objects.order_by('order'))

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'formset': formset}
    return render(request, 'common/position.html', context)


@login_required(login_url='common:login')
def holiday(request):
    year = datetime.today().year
    search_year = request.GET.get('search', year)

    HolidayFormSet = modelformset_factory(model=Holiday, form=HolidayForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = HolidayFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:holiday')

        if formset.is_valid():
            holidays = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for holiday in holidays:
                holiday.reg_id = request.user
                holiday.reg_date = timezone.now()
                holiday.mod_id = request.user
                holiday.mod_date = timezone.now()
                holiday.save()

            return redirect('common:holiday')
    else:
        if search_year == '전체':
            formset = HolidayFormSet(queryset=Holiday.objects.order_by('holiday', 'holiday_name'))
        else:
            formset = HolidayFormSet(queryset=Holiday.objects.order_by('holiday', 'holiday_name').filter(holiday__year=search_year))

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    # 년도별 공휴일을 검색하기 위해 QuerySet을 해당값만으로 리스트 구성(flat)하고, 중복제거(distinct)
    year_list = list(Holiday.objects.annotate(
        year=ExtractYear('holiday')).values_list('year', flat=True).distinct())
    context = {'formset': formset, 'year_list': year_list, 'search_year': search_year}
    return render(request, 'common/holiday.html', context)


@login_required(login_url='common:login')
def business(request):
    BusinessFormSet = modelformset_factory(model=Business, form=BusinessForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = BusinessFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:business')

        if formset.is_valid():
            businesses = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for business in businesses:
                business.reg_id = request.user
                business.reg_date = timezone.now()
                business.mod_id = request.user
                business.mod_date = timezone.now()
                business.save()

            return redirect('common:business')
    else:
        formset = BusinessFormSet()

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'formset': formset}
    return render(request, 'common/business.html', context)


@login_required(login_url='common:login')
def code(request):
    search = request.GET.get('search', '전체')

    CodeFormSet = modelformset_factory(model=Code, form=CodeForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = CodeFormSet(request.POST)
        if not formset.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('common:code')

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

            return redirect('common:code')
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
    return render(request, 'common/code.html', context)
