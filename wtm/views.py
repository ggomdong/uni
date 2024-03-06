from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import connection
from common.models import User
from .models import Work, Module, Contract, Schedule
from .forms import ModuleForm, ContractForm
from django.utils import timezone
from common import context_processors
from datetime import datetime


@login_required(login_url='common:login')
def index(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
    return render(request, 'wtm/index.html', context)


@login_required(login_url='common:login')
def work_module(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
    return render(request, 'wtm/work_module.html', context)


@login_required(login_url='common:login')
def work_module_reg(request):
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.reg_id = request.user
            module.reg_date = timezone.now()
            module.mod_id = request.user
            module.mod_date = timezone.now()
            module.save()
            return redirect('wtm:work_module')
    else:
        form = ModuleForm()
    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'form': form}
    return render(request, 'wtm/work_module_reg.html', context)


@login_required(login_url='common:login')
def work_module_modify(request, module_id):
    module = get_object_or_404(Module, pk=module_id)

    # if request.user != question.author:
    #     messages.error(request, '수정권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question_id)
    # 수정화면에서 저장하기 버튼 클릭시 POST 방식으로 데이터 수정
    if request.method == 'POST':
        # 수정된 내용을 반영하기 위해, request에서 넘어온 값으로 덮어쓰라는 의미
        form = ModuleForm(request.POST, instance=module)

        if not form.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('wtm:work_module_modify', module_id=module_id)
        if form.is_valid():
            module = form.save(commit=False)
            module.mod_id = request.user
            module.mod_date = timezone.now()
            module.save()
            return redirect('wtm:work_module')
    # GET 방식으로 수정화면 호출
    else:
        # 대상이 유지되어야 하므로, instance=module 과 같이 생성
        form = ModuleForm(instance=module)

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'form': form}
    return render(request, 'wtm/work_module_reg.html', context)


@login_required(login_url='common:login')
def work_module_delete(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)
    module.delete()
    return redirect('wtm:work_module')


@login_required(login_url='common:login')
def work_contract_reg(request, user_id):
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.user_id = user_id
            contract.reg_id = request.user
            contract.reg_date = timezone.now()
            contract.mod_id = request.user
            contract.mod_date = timezone.now()
            contract.save()
            return redirect('common:user_modify', user_id=user_id)
    else:
        form = ContractForm()

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    target_user = get_object_or_404(User, pk=user_id)  # 근로계약 대상 표시를 위함
    module_list = Module.objects.all()  # 근로모듈을 요일별로 입력하기 위함
    context = {'form': form, 'target_user': target_user, 'module_list': module_list}
    return render(request, 'wtm/work_contract_reg.html', context)


@login_required(login_url='common:login')
def work_contract_modify(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    # 수정시 포맷이 달라서 기준일자가 유지되지 않는 문제 해결을 위해 포맷을 미리 지정
    contract.stand_date = contract.stand_date.strftime("%Y-%m-%d")
    user_id = contract.user_id

    # if request.user != question.author:
    #     messages.error(request, '수정권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question_id)
    # 수정화면에서 저장하기 버튼 클릭시 POST 방식으로 데이터 수정
    if request.method == 'POST':
        # 수정된 내용을 반영하기 위해, request에서 넘어온 값으로 덮어쓰라는 의미
        form = ContractForm(request.POST, instance=contract)

        if not form.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('wtm:work_contract_modify', module_id=contract_id)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.mod_id = request.user
            contract.mod_date = timezone.now()
            contract.save()
            return redirect('common:user_modify', user_id=user_id)
    # GET 방식으로 수정화면 호출
    else:
        # 대상이 유지되어야 하므로, instance=contract 와 같이 생성
        form = ContractForm(instance=contract)

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    target_user = get_object_or_404(User, pk=user_id)  # 근로계약 대상 표시를 위함
    module_list = Module.objects.all()  # 근로모듈을 요일별로 입력하기 위함

    context = {'form': form, 'target_user': target_user, 'module_list': module_list}
    return render(request, 'wtm/work_contract_reg.html', context)


@login_required(login_url='common:login')
def work_contract_delete(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    user_id = contract.user_id
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)
    contract.delete()
    return redirect('common:user_modify', user_id=user_id)


@login_required(login_url='common:login')
def work_schedule(request, stand_ym=None):
    # 기준년월 값이 없으면 현재로 세팅
    if stand_ym is None:
        stand_ym = str(datetime.today().year) + str(datetime.today().month).zfill(2)

    raw_query = f'''
        SELECT s.id as sid, u.id as uid, u.emp_name, u.dept, u.position,
            DATE_FORMAT(u.join_date, '%Y%m%d') join_date, DATE_FORMAT(u.out_date, '%Y%m%d') out_date,
            s.d1_id d1, s.d2_id d2, s.d3_id d3, s.d4_id d4, s.d5_id d5, s.d6_id d6, s.d7_id d7, s.d8_id d8,
            s.d9_id d9, s.d10_id d10, s.d11_id d11, s.d12_id d12, s.d13_id d13, s.d14_id d14, s.d15_id d15,
            s.d16_id d16, s.d17_id d17, s.d18_id d18, s.d19_id d19, s.d20_id d20, s.d21_id d21, s.d22_id d22,
            s.d23_id d23, s.d24_id d24, s.d25_id d25, s.d26_id d26, s.d27_id d27, s.d28_id d28, s.d29_id d29,
            s.d30_id d30, s.d31_id d31,
            d.order as do, p.order as po
        FROM wtm_schedule s
            INNER JOIN common_user u on (s.user_id = u.id)
            INNER JOIN common_dept d on (u.dept = d.dept_name)
            INNER JOIN common_position p on (u.position = p.position_name)
        WHERE year = '{stand_ym[0:4]}'
          and month = '{stand_ym[4:6]}'
        ORDER BY do, po, join_date
        '''

    with connection.cursor() as cursor:
        cursor.execute(raw_query)
        results = cursor.fetchall()

        x = cursor.description
        schedule_list = []
        for r in results:
            i = 0
            d = {}
            while i < len(x):
                d[x[i][0]] = r[i]
                i = i + 1
            schedule_list.append(d)

    # 부서간 구분선 표기를 위해 직전 직원의 부서명을 저장할 변수 설정
    pre_dept = None

    # user_list에 일자별 근무모듈을 매핑
    for schedule in schedule_list:
        # 직전 직원의 부서명과 비교해서 같으면 'N'을 다르면 'Y' 세팅
        schedule['dept_diff'] = ('N' if pre_dept == schedule['dept'] else 'Y')
        pre_dept = schedule['dept']

    day_list = context_processors.get_day_list(stand_ym)
    module_list = Module.objects.all()  # 근로모듈

    context = {'schedule_list': schedule_list, 'day_list': day_list, 'module_list': module_list, 'stand_ym': stand_ym}
    return render(request, 'wtm/work_schedule.html', context)


@login_required(login_url='common:login')
def work_schedule_reg(request, stand_ym):
    if request.method == 'POST':
        # html form에서 넘어오는 값은 'sch_"user_id"_"day"': 'value' 형태임
        # 이를 Schedule 테이블에 user단위로 넣기 위해 schedule_row라는 dict로 정리하고,
        # 해당 row를 담을 schedule_list를 만든다.
        schedule_list = []
        schedule_row = {
            'user_id': None, 'd1': None, 'd2': None, 'd3': None, 'd4': None, 'd5': None, 'd6': None, 'd7': None,
            'd8': None, 'd9': None, 'd10': None, 'd11': None, 'd12': None, 'd13': None, 'd14': None, 'd15': None,
            'd16': None, 'd17': None, 'd18': None, 'd19': None, 'd20': None, 'd21': None, 'd22': None, 'd23': None,
            'd24': None, 'd25': None, 'd26': None, 'd27': None, 'd28': None, 'd29': None, 'd30': None, 'd31': None,
        }

        for key, value in request.POST.items():
            # sch로 시작하는 key만 대상으로 함
            if key.startswith('sch'):
                # 최초 schedule_row['user_id'] 값을 세팅
                if schedule_row['user_id'] == None:
                    schedule_row['user_id'] = key.split("_")[1]
                # user_id가 바뀌면 schedule_row를 list에 넣어준다. 이때 참조가 아닌 값으로 넣기위해 copy를 선행함
                elif schedule_row['user_id'] != key.split("_")[1]:
                    dummy = schedule_row.copy()
                    schedule_list.append(dummy)
                    # schedule_row['user_id']를 바뀐 값으로 세팅
                    schedule_row['user_id'] = key.split("_")[1]

                schedule_row["d" + key.split("_")[2]] = (None if value == '' else Module.objects.get(id=value))

        # 마지막 요소를 list에 추가
        dummy = schedule_row.copy()
        schedule_list.append(dummy)
        # print(schedule_list)

        for schedule in schedule_list:
            obj = Schedule(
                user_id=schedule['user_id'],
                year=stand_ym[0:4],
                month=stand_ym[4:6],
                d1=schedule['d1'],
                d2=schedule['d2'],
                d3=schedule['d3'],
                d4=schedule['d4'],
                d5=schedule['d5'],
                d6=schedule['d6'],
                d7=schedule['d7'],
                d8=schedule['d8'],
                d9=schedule['d9'],
                d10=schedule['d10'],
                d11=schedule['d11'],
                d12=schedule['d12'],
                d13=schedule['d13'],
                d14=schedule['d14'],
                d15=schedule['d15'],
                d16=schedule['d16'],
                d17=schedule['d17'],
                d18=schedule['d18'],
                d19=schedule['d19'],
                d20=schedule['d20'],
                d21=schedule['d21'],
                d22=schedule['d22'],
                d23=schedule['d23'],
                d24=schedule['d24'],
                d25=schedule['d25'],
                d26=schedule['d26'],
                d27=schedule['d27'],
                d28=schedule['d28'],
                d29=schedule['d29'],
                d30=schedule['d30'],
                d31=schedule['d31'],
                reg_id=request.user,
                reg_date=timezone.now(),
                mod_id=request.user,
                mod_date=timezone.now(),
            )
            obj.save()

        return redirect('wtm:work_schedule', stand_ym=stand_ym)

    ############ GET방식일때 아래로 진행 ############
    day_list = context_processors.get_day_list(stand_ym)  # ex) {'1':'목', '2':'금', ..., '31':'토'}

    # 직원별 근로계약 컬럼을 참조하기 위해 day_list를 요일의 영문값으로 세팅
    week_dict = context_processors.day_of_the_week  # {'mon': '월', 'tue': '화', 'wed': '수', 'thu': '목', 'fri': '금', 'sat': '토', 'sun': '일', }
    day_list_eng = {}
    for key, value in day_list.items():
        day_list_eng[key] = list(week_dict.keys())[list(week_dict.values()).index(value)]

    # 입사일자가 근무표 말일 이전인 직원만 대상으로 하기 위해 변수 할당, list(day_list)[-1]은 말일
    schedule_date = stand_ym + list(day_list)[-1]
    # schedule_date = datetime.strptime(stand_ym + list(day_list)[-1], '%Y%m%d')

    # stand_ym 대상 직원을 추출하여 user_list에 저장
    query_user = f'''
        SELECT u.id, u.emp_name, u.dept, u.position,
                DATE_FORMAT(u.join_date, '%Y%m%d') join_date, DATE_FORMAT(u.out_date, '%Y%m%d') out_date,
                d.order as do, p.order as po
        FROM common_user u
            INNER JOIN common_dept d on (u.dept = d.dept_name)
            INNER JOIN common_position p on (u.position = p.position_name)
        WHERE is_superuser = false 
            and DATE_FORMAT(u.join_date, '%Y%m%d') <= '{schedule_date}'
            and (DATE_FORMAT(u.out_date, '%Y%m%d') is null or DATE_FORMAT(u.out_date, '%Y%m%d') >= '{stand_ym + '01'}')
        ORDER BY do, po, join_date
        '''
    with connection.cursor() as cursor:
        cursor.execute(query_user)
        results = cursor.fetchall()

        x = cursor.description
        user_list = []
        for r in results:
            i = 0
            d = {}
            while i < len(x):
                d[x[i][0]] = r[i]
                i = i + 1
            user_list.append(d)

    # 부서간 구분선 표기를 위해 직전 직원의 부서명을 저장할 변수 설정
    pre_dept = None

    # user_list에 일자별 근무모듈을 매핑
    for user in user_list:
        for key, value in day_list_eng.items():
            query = f'''
                SELECT c.val
                FROM
                (
                SELECT row_number() over (order by stand_date desc) as rownum , wtm_contract.{value}_id as val
                FROM wtm_contract
                WHERE user_id = {user['id']}
                  and DATE_FORMAT(stand_date, '%Y%m%d') <= '{stand_ym + key.zfill(2)}'
                ) c
                WHERE rownum = 1
                '''
            with connection.cursor() as cursor:
                cursor.execute(query)
                r = cursor.fetchone()

            user[key] = (None if r == None else r[0])

        # 직전 직원의 부서명과 비교해서 같으면 'N'을 다르면 'Y' 세팅
        user['dept_diff'] = ('N' if pre_dept == user['dept'] else 'Y')
        pre_dept = user['dept']

    # print(user_list)

    module_list = Module.objects.all()  # 근로모듈을 입력하기 위함
    context = {'stand_ym': stand_ym, 'day_list': day_list, 'user_list': user_list, 'module_list': module_list}
    return render(request, 'wtm/work_schedule_reg.html', context)


@login_required(login_url='common:login')
def work_schedule_modify(request, stand_ym):
    day_list = context_processors.get_day_list(stand_ym)
    # 직원별 근로계약 컬럼을 참조하기 위해 day_list를 요일의 영문값으로도 세팅
    week_dict = context_processors.day_of_the_week  # {'mon': '월', 'tue': '화', 'wed': '수', 'thu': '목', 'fri': '금', 'sat': '토', 'sun': '일', }

    day_list_eng = {}
    for key, value in day_list.items():
        day_list_eng[key] = list(week_dict.keys())[list(week_dict.values()).index(value)]




    schedule_list = list(Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6]).values())
    module_list = Module.objects.all()  # 근로모듈

    print(schedule_list)

    context = {'schedule_list': schedule_list, 'day_list': day_list, 'module_list': module_list, 'stand_ym': stand_ym}
    return render(request, 'wtm/work_schedule_modify.html', context)


@login_required(login_url='common:login')
def work_schedule_delete(request, stand_ym):
    schedule = Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6])
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)
    schedule.delete()
    return redirect('wtm:work_schedule', stand_ym=stand_ym)


@login_required(login_url='common:login')
def work_status(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
    return render(request, 'wtm/work_status.html', context)


@login_required(login_url='common:login')
def work_log(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
    return render(request, 'wtm/work_log.html', context)
