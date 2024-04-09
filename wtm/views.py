from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import ExtractDay
from django.db import connection, transaction
from common.models import User, Holiday
from .models import Work, Module, Contract, Schedule
from .forms import ModuleForm, ContractForm
from django.utils import timezone
from common import context_processors
from datetime import datetime


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


def work_schedule(request, stand_ym=None):
    # 기준년월 값이 없으면 현재로 세팅
    if stand_ym is None:
        stand_ym = str(datetime.today().year) + str(datetime.today().month).zfill(2)

    # stand_ym 기준 스케쥴이 없으면 패스
    if Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6]).count() == 0:
        redirect('wtm:work_schedule', stand_ym=stand_ym)

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
            LEFT OUTER JOIN common_user u on (s.user_id = u.id)
            LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name)
            LEFT OUTER JOIN common_position p on (u.position = p.position_name)
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

    # 공휴일 날짜만 추출하여 list로 만듬. ex) [1, 9, 10, 11]
    holiday_list = list(Holiday.objects.filter(holiday__year=stand_ym[0:4], holiday__month=stand_ym[4:6]).annotate(
        day=ExtractDay('holiday')).values_list('day', flat=True))

    # 입사일자가 근무표 말일 이전인 직원만 대상으로 하기 위해 변수 할당, list(day_list)[-1]은 말일
    schedule_date = stand_ym + list(day_list)[-1]

    # 다음달 일요일까지 날짜를 추가하기 위한 로직
    # 1.마지막날의 요일값을 확인(6-요일값 만큼의 일자가 있음) 2.해당 날짜들로 구성된 day_list 작성
    # 3.next_ym 기준 공휴일 list 생성 4.schedule_list에 next_ym 기준 스케쥴 추가
    last_day_weekday = context_processors.get_weekday(schedule_date)

    # 말일이 일요일일 경우에 아예 해당 변수를 만들지 않으면 context에서 오류가 발생하므로, 전달할 변수는 모두 초기화
    next_ym = None
    next_day_list = None
    next_holiday_list = None

    # last_day_weekday가 6(일요일)이면 패스
    if last_day_weekday != 6:
        # 다음달 년월 산출
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]
        next_day_list = context_processors.get_day_list(next_ym, 6-last_day_weekday)
        next_holiday_list = list(Holiday.objects.filter(holiday__year=next_ym[0:4], holiday__month=next_ym[4:6]).annotate(
            day=ExtractDay('holiday')).values_list('day', flat=True))

        for schedule in schedule_list:
            raw_query = f'''
                SELECT s.d1_id '1', s.d2_id '2', s.d3_id '3', s.d4_id '4', s.d5_id '5', s.d6_id '6'
                FROM wtm_schedule s
                WHERE year = '{next_ym[0:4]}'
                  and month = '{next_ym[4:6]}'
                  and user_id = '{schedule["uid"]}'
                '''
            with connection.cursor() as cursor:
                cursor.execute(raw_query)
                results = cursor.fetchall()

                if results:
                    x = cursor.description
                    for r in results:
                        i = 0
                        while i < len(x):
                            schedule[x[i][0]] = r[i]
                            i = i + 1

    # 근무표와 직원현황이 다른 경우 1 : 스케쥴 작성 이후 추가된 직원이 있는 경우 (user minus schedule)
    raw_query = f'''
        SELECT emp_name
        FROM
        (
            SELECT id, emp_name
            FROM common_user u
            WHERE is_superuser = false 
                and DATE_FORMAT(u.join_date, '%Y%m%d') <= '{schedule_date}'
                and (DATE_FORMAT(u.out_date, '%Y%m%d') is null or DATE_FORMAT(u.out_date, '%Y%m%d') >= '{stand_ym + '01'}')
        ) a
        LEFT JOIN
        (
            SELECT u.id
            FROM wtm_schedule s
                LEFT OUTER JOIN common_user u on (s.user_id = u.id)
            WHERE year = '{stand_ym[0:4]}'
              and month = '{stand_ym[4:6]}'
        ) b
        on a.id = b.id
        WHERE b.id is null
        '''

    with connection.cursor() as cursor:
        cursor.execute(raw_query)
        results = cursor.fetchall()

        need_to_add = []
        for r in results:
            need_to_add.append(r[0])

    if schedule_list and need_to_add:
        messages.warning(request, f'근무표 추가 필요 : {need_to_add}')
        redirect('wtm:work_schedule', stand_ym=stand_ym)

    # 근무표와 직원현황이 다른 경우 2 : 스케쥴 작성 이후 삭제 또는 입사일 변경 등 직원이 있는 경우 (schedule minus user)
    raw_query = f'''
        SELECT b.emp_name
        FROM
        (
            SELECT u.id, u.emp_name
            FROM wtm_schedule s
                LEFT OUTER JOIN common_user u on (s.user_id = u.id)
            WHERE year = '{stand_ym[0:4]}'
              and month = '{stand_ym[4:6]}'
        ) b        
        LEFT JOIN
        (
            SELECT id
            FROM common_user u
            WHERE is_superuser = false 
                and DATE_FORMAT(u.join_date, '%Y%m%d') <= '{schedule_date}'
                and (DATE_FORMAT(u.out_date, '%Y%m%d') is null or DATE_FORMAT(u.out_date, '%Y%m%d') >= '{stand_ym + '01'}')
        ) a
        on b.id = a.id
        WHERE a.id is null
        '''

    with connection.cursor() as cursor:
        cursor.execute(raw_query)
        results = cursor.fetchall()

        need_to_sub = []
        for r in results:
            need_to_sub.append(r[0])

    if schedule_list and need_to_sub:
        messages.warning(request, f'근무표 제외 필요 : {need_to_sub}')
        redirect('wtm:work_schedule', stand_ym=stand_ym)

    context = {'schedule_list': schedule_list, 'day_list': day_list, 'module_list': module_list, 'stand_ym': stand_ym,
               'holiday_list': holiday_list, 'next_day_list': next_day_list, 'next_holiday_list': next_holiday_list,
               'next_ym': next_ym}
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
            'n1': None, 'n2': None, 'n3': None, 'n4': None, 'n5': None, 'n6': None,
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

                # n으로 시작하면 다음달, 아니면 이번달
                if key.split("_")[2].startswith('n'):
                    schedule_row[key.split("_")[2]] = (None if value == '' else Module.objects.get(id=value))
                else:
                    schedule_row["d" + key.split("_")[2]] = (None if value == '' else Module.objects.get(id=value))

        # 마지막 요소를 list에 추가
        dummy = schedule_row.copy()
        schedule_list.append(dummy)

        # stand_ym 기준 기존 스케쥴이 입력되어 있는 user_id를 가져옴
        schedule_user_list = list(
            Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6]).values_list('user_id', flat=True))

        # 다음달 근무표를 저장하기 위한 변수
        # 1.마지막날의 요일값을 확인(6-요일값 만큼의 일자가 있음) 2.next_ym 계산
        schedule_date = stand_ym + str(context_processors.get_last_day(stand_ym))
        last_day_weekday = context_processors.get_weekday(schedule_date)
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]

        with transaction.atomic():
            for schedule in schedule_list:
                # 기존 스케쥴이 있는 경우 저장하지 않음(정상적인 루트로는 불가능하지만, url을 치고 들어온다거나 하는 케이스)
                if int(schedule['user_id']) in schedule_user_list:
                    messages.error(request, '중복된 스케쥴입니다.')
                    redirect('wtm:work_schedule', stand_ym=stand_ym)
                # 기존 스케쥴이 없는 경우 저장
                else:
                    # stand_ym 대상에 대한 입력 처리
                    # 직원의 입사일이 stand_ym의 말일보다 크면, stand_ym 기준 스케쥴은 없으므로 패스함
                    user = User.objects.get(pk=schedule['user_id'])
                    if stand_ym < user.join_date.strftime('%Y%m'):
                        pass
                    else:
                        try:
                            obj1 = Schedule(
                                user_id=schedule['user_id'],
                                year=stand_ym[0:4],
                                month=stand_ym[4:6],
                                reg_id=request.user,
                                reg_date=timezone.now(),
                                mod_id=request.user,
                                mod_date=timezone.now(),
                            )

                            # 일자별 스케쥴 대입. ex)obj1.d1 = schedule['d1']
                            for i in range(1, int(schedule_date[6:8]) + 1):
                                setattr(obj1, f'd{i}', schedule[f'd{i}'])

                            obj1.save()
                        except Exception as e:
                            messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                            redirect('wtm:work_schedule_reg', stand_ym=stand_ym)

                    # 말일이 일요일이 아니면, 다음달 일요일까지 입력이 필요함
                    # 단, 다음달의 스케쥴이 이미 있는 경우, 중복이 되지 않도록 update로 처리
                    if last_day_weekday != 6:
                        # 직원의 최종근무일이 next_ym의 1일보다 작으면, next_ym 기준 스케쥴은 없으므로 패스함
                        if user.out_date is not None and user.out_date.strftime('%Y%m') < next_ym:
                            pass
                        else:
                            # next_ym 기준 기존 스케쥴이 입력되어 있는 user_id를 가져옴
                            next_schedule_user_list = list(
                                Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6]).values_list('user_id', flat=True))

                            # 기존 스케쥴이 존재하는 경우 기존 schedule을 수정
                            if int(schedule['user_id']) in next_schedule_user_list:
                                try:
                                    obj2 = Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6],
                                                                   user_id=schedule['user_id'])
                                    obj_to_update = obj2[0]

                                    obj_to_update.mod_id=request.user
                                    obj_to_update.mod_date=timezone.now()

                                    # 일자별 스케쥴 대입. ex)obj_to_update.d1 = schedule['n1']
                                    # 단순히 n1~n6을 모두 업데이트하면, 일요일 이후는 None으로 매핑되므로, 기존 스케쥴이 None으로 바뀔 수 있음
                                    # 따라서, 정확히 필요한 날짜만 계산해서 업데이트 필수적
                                    for i in range(1, 6 - last_day_weekday + 1):
                                        setattr(obj_to_update, f'd{i}', schedule[f'n{i}'])

                                    obj_to_update.save()
                                except Exception as e:
                                    messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                                    redirect('wtm:work_schedule_reg', stand_ym=stand_ym)

                            # 기존 스케쥴이 없는 경우 insert
                            else:
                                try:
                                    obj2 = Schedule(
                                        user_id=schedule['user_id'],
                                        year=next_ym[0:4],
                                        month=next_ym[4:6],
                                        reg_id=request.user,
                                        reg_date=timezone.now(),
                                        mod_id=request.user,
                                        mod_date=timezone.now(),
                                    )

                                    # 일자별 스케쥴 대입. ex)obj2.d1 = schedule['n1']
                                    for i in range(1, 6 - last_day_weekday + 1):
                                        setattr(obj2, f'd{i}', schedule[f'n{i}'])

                                    obj2.save()
                                except Exception as e:
                                    messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                                    redirect('wtm:work_schedule_reg', stand_ym=stand_ym)

        return redirect('wtm:work_schedule', stand_ym=stand_ym)

    ###########################################
    ############ GET방식일때 아래로 진행 ############
    ###########################################
    day_list = context_processors.get_day_list(stand_ym)  # ex) {'1':'목', '2':'금', ..., '31':'토'}

    # 직원별 근로계약 컬럼을 참조하기 위해 day_list를 요일의 영문값으로 세팅
    week_dict = context_processors.day_of_the_week  # {'mon': '월', 'tue': '화', 'wed': '수', 'thu': '목', 'fri': '금', 'sat': '토', 'sun': '일', }
    day_list_eng = {}
    for key, value in day_list.items():
        day_list_eng[key] = list(week_dict.keys())[list(week_dict.values()).index(value)]

    # 기준이 되는 최종 일요일(이번달 말일이 일요일인 경우 or 다음달 첫 일요일) 날짜를 지정 -> 해당 날짜 기준으로 대상 직원 추출
    schedule_date = stand_ym + list(day_list)[-1]
    last_day_weekday = context_processors.get_weekday(schedule_date)

    # 말일이 일요일인 경우에 아예 해당 변수를 만들지 않으면 context에서 오류가 발생하므로, 전달할 변수는 일단 모두 초기화
    next_ym = None
    next_day_list = None
    next_holiday_list = None

    # last_day_weekday가 6(일요일)이면 stand_ym 기준 말일이 기준일자
    # last_day_weekday가 6(일요일)이 아니면, next_ym 기준 첫 일요일이 기준일자
    if last_day_weekday != 6:
        # 다음달 년월을 산출하고, 첫째 일요일인 날짜(6-last_day_weekday)를 붙여서 schedule_date를 재정의
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]
        schedule_date = next_ym + str(6-last_day_weekday).zfill(2)

    # 대상 직원을 추출하여 user_list에 저장
    query_user = f'''
        SELECT u.id, u.emp_name, u.dept, u.position,
                DATE_FORMAT(u.join_date, '%Y%m%d') join_date, DATE_FORMAT(u.out_date, '%Y%m%d') out_date,
                d.order as do, p.order as po
        FROM common_user u
            LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name)
            LEFT OUTER JOIN common_position p on (u.position = p.position_name)
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

    # 공휴일 날짜만 추출하여 list로 만듬. ex) [1, 9, 10, 11]
    holiday_list = list(Holiday.objects.filter(holiday__year=stand_ym[0:4], holiday__month=stand_ym[4:6]).annotate(
        day=ExtractDay('holiday')).values_list('day', flat=True))

    # 공휴일은 OFF 모듈로 지정하기 위해 OFF 모듈의 ID 추출
    off_module_list = list(Module.objects.filter(cat='OFF').values_list('id', flat=True))
    off_module_id = (off_module_list[0] if off_module_list else None)

    # 부서간 구분선 표기를 위해 직전 직원의 부서명을 저장할 변수 설정
    pre_dept = None

    # user_list에 일자별 근무모듈을 매핑
    for user in user_list:
        for key, value in day_list_eng.items():
            # 입사 전이나, 최종근무일 후라면 None으로 세팅
            if stand_ym + key.zfill(2) < user['join_date'] or (
                    user['out_date'] is not None and stand_ym + key.zfill(2) > user['out_date']):
                user[key] = None
            # 공휴일이면 OFF 모듈로 세팅
            elif int(key) in holiday_list:
                user[key] = off_module_id
            else:
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

    # 다음달 일요일까지 날짜를 추가하기 위한 로직
    # 1.마지막날의 요일값을 확인(6-요일값 만큼의 일자가 있음) 2.해당 날짜들로 구성된 day_list 작성
    # 3.next_ym 기준 공휴일 list 생성 4.user_list에 next_ym 기준 스케쥴 추가
    # last_day_weekday가 6(일요일)이면 패스
    if last_day_weekday != 6:
        next_day_list = context_processors.get_day_list(next_ym, 6-last_day_weekday)
        next_day_list_eng = {}
        for key, value in next_day_list.items():
            next_day_list_eng[key] = list(week_dict.keys())[list(week_dict.values()).index(value)]
        next_holiday_list = list(
            Holiday.objects.filter(holiday__year=next_ym[0:4], holiday__month=next_ym[4:6]).annotate(
                day=ExtractDay('holiday')).values_list('day', flat=True))

        # 기존 스케쥴이 입력되어 있는 user_id를 가져옴
        next_schedule_user_list = list(
            Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6]).values_list('user_id', flat=True))

        # 스케쥴을 가져옴
        next_schedule_origin = Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6])

        # user_list에 일자별 근무모듈을 매핑
        for user in user_list:
            # 기존 스케쥴이 있는 경우 schedule에서 가져옴
            if user['id'] in next_schedule_user_list:
                for key, value in next_day_list.items():
                    user["n"+key] = list(next_schedule_origin.filter(user_id=user['id']).values_list('d' + key + '_id', flat=True))[0]
            # 기존 스케쥴이 없는 경우 공휴일 세팅 및 contract에서 가져옴
            else:
                for key, value in next_day_list_eng.items():
                    # 입사 전이나, 최종근무일 후라면 None으로 세팅
                    if next_ym + key.zfill(2) < user['join_date'] or (
                            user['out_date'] is not None and next_ym + key.zfill(2) > user['out_date']):
                        user["n"+key] = None
                    # 공휴일이면 OFF 모듈로 세팅
                    elif int(key) in next_holiday_list:
                        user["n"+key] = off_module_id
                    else:
                        query = f'''
                                SELECT c.val
                                FROM
                                (
                                SELECT row_number() over (order by stand_date desc) as rownum , wtm_contract.{value}_id as val
                                FROM wtm_contract
                                WHERE user_id = {user['id']}
                                  and DATE_FORMAT(stand_date, '%Y%m%d') <= '{next_ym + key.zfill(2)}'
                                ) c
                                WHERE rownum = 1
                                '''
                        with connection.cursor() as cursor:
                            cursor.execute(query)
                            r = cursor.fetchone()

                        user["n"+key] = (None if r == None else r[0])

    module_list = Module.objects.all()  # 근로모듈을 입력하기 위함

    context = {'stand_ym': stand_ym, 'day_list': day_list, 'user_list': user_list, 'module_list': module_list,
               'holiday_list': holiday_list, 'next_day_list': next_day_list, 'next_holiday_list': next_holiday_list,
               'next_ym': next_ym}
    return render(request, 'wtm/work_schedule_reg.html', context)


@login_required(login_url='common:login')
def work_schedule_modify(request, stand_ym):
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
            'n1': None, 'n2': None, 'n3': None, 'n4': None, 'n5': None, 'n6': None,
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

                # n으로 시작하면 다음달, 아니면 이번달
                if key.split("_")[2].startswith('n'):
                    schedule_row[key.split("_")[2]] = (None if value == '' else Module.objects.get(id=value))
                else:
                    schedule_row["d" + key.split("_")[2]] = (None if value == '' else Module.objects.get(id=value))

        # 마지막 요소를 list에 추가
        dummy = schedule_row.copy()
        schedule_list.append(dummy)

        # stand_ym 기준 기존 스케쥴이 입력되어 있는 user_id를 가져옴
        schedule_user_list = list(
            Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6]).values_list('user_id', flat=True))

        # 다음달 근무표를 저장하기 위한 변수
        # 1.마지막날의 요일값을 확인(6-요일값 만큼의 일자가 있음) 2.next_ym 계산
        schedule_date = stand_ym + str(context_processors.get_last_day(stand_ym))
        last_day_weekday = context_processors.get_weekday(schedule_date)
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]

        with transaction.atomic():
            # 삭제 대상이면(기존 스케쥴은 있었으나, 현재 추출한 schedule_list에 없는 경우), 해당 schedule을 삭제
            for user in schedule_user_list:
                if user not in [int(item['user_id']) for item in schedule_list]:
                    try:
                        schedule_to_delete = Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6],
                                                                     user_id=user)
                        schedule_to_delete.delete()
                    except Exception as e:
                        messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                        redirect('wtm:work_schedule', stand_ym=stand_ym)

            for schedule in schedule_list:
                user = User.objects.get(pk=schedule['user_id'])
                # 기존 스케쥴이 존재하는 경우 기존 schedule을 수정
                if int(schedule['user_id']) in schedule_user_list:
                    try:
                        obj = Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6],
                                                      user_id=schedule['user_id'])
                        obj_to_update = obj[0]

                        obj_to_update.mod_id = request.user
                        obj_to_update.mod_date = timezone.now()

                        # 일자별 스케쥴 대입. ex)obj_to_update.d1 = schedule['d1']
                        for i in range(1, int(schedule_date[6:8]) + 1):
                            setattr(obj_to_update, f'd{i}', schedule[f'd{i}'])

                        obj_to_update.save()
                    except Exception as e:
                        messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                        redirect('wtm:work_schedule_modify', stand_ym=stand_ym)

                # 기존 스케쥴이 없는 경우 insert
                else:
                    # 직원의 입사일이 stand_ym의 말일보다 크면, stand_ym 기준 스케쥴은 없으므로 패스함
                    if stand_ym < user.join_date.strftime('%Y%m'):
                        pass
                    else:
                        try:
                            obj = Schedule(
                                user_id=schedule['user_id'],
                                year=stand_ym[0:4],
                                month=stand_ym[4:6],
                                reg_id=request.user,
                                reg_date=timezone.now(),
                                mod_id=request.user,
                                mod_date=timezone.now(),
                            )

                            # 일자별 스케쥴 대입. ex)obj1.d1 = schedule['d1']
                            for i in range(1, int(schedule_date[6:8]) + 1):
                                setattr(obj, f'd{i}', schedule[f'd{i}'])

                            obj.save()
                        except Exception as e:
                            messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                            redirect('wtm:work_schedule_modify', stand_ym=stand_ym)

                # 말일이 일요일이 아니면, 다음달 일요일까지 입력이 필요함
                # 단, 다음달의 스케쥴이 이미 있는 경우, 중복이 되지 않도록 update로 처리
                if last_day_weekday != 6:
                    # 직원의 최종근무일이 next_ym의 1일보다 작으면, next_ym 기준 스케쥴은 없으므로 패스함
                    if user.out_date is not None and user.out_date.strftime('%Y%m') < next_ym:
                        pass
                    else:
                        # next_ym 기준 기존 스케쥴이 입력되어 있는 user_id를 가져옴
                        next_schedule_user_list = list(
                            Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6]).values_list(
                                'user_id', flat=True))

                        # 기존 스케쥴이 존재하는 경우 기존 schedule을 수정
                        if int(schedule['user_id']) in next_schedule_user_list:
                            try:
                                obj2 = Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6],
                                                               user_id=schedule['user_id'])
                                obj_to_update = obj2[0]

                                obj_to_update.mod_id = request.user
                                obj_to_update.mod_date = timezone.now()

                                # 일자별 스케쥴 대입. ex)obj_to_update.d1 = schedule['n1']
                                # 단순히 n1~n6을 모두 업데이트하면, 일요일 이후는 None으로 매핑되므로, 기존 스케쥴이 None으로 바뀔 수 있음
                                # 따라서, 정확히 필요한 날짜만 계산해서 업데이트 필수적
                                for i in range(1, 6 - last_day_weekday + 1):
                                    setattr(obj_to_update, f'd{i}', schedule[f'n{i}'])

                                obj_to_update.save()
                            except Exception as e:
                                messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                                redirect('wtm:work_schedule_modify', stand_ym=stand_ym)

                        # 기존 스케쥴이 없는 경우 insert
                        else:
                            try:
                                obj2 = Schedule(
                                    user_id=schedule['user_id'],
                                    year=next_ym[0:4],
                                    month=next_ym[4:6],
                                    reg_id=request.user,
                                    reg_date=timezone.now(),
                                    mod_id=request.user,
                                    mod_date=timezone.now(),
                                )

                                # 일자별 스케쥴 대입. ex)obj2.d1 = schedule['n1']
                                for i in range(1, 6 - last_day_weekday + 1):
                                    setattr(obj2, f'd{i}', schedule[f'n{i}'])

                                obj2.save()
                            except Exception as e:
                                messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
                                redirect('wtm:work_schedule_modify', stand_ym=stand_ym)

        return redirect('wtm:work_schedule', stand_ym=stand_ym)

    ############ GET방식일때 아래로 진행 ############
    # 근무표 수정 기능 설명
    # 1. 해당 stand_ym의 대상 직원 추출
    # 2. 공휴일, 영업일 세팅
    # 3. 기존 스케쥴 있으면 스케쥴을 가져오고, 없으면 근로계약에서 가져옴
    ##############################################

    day_list = context_processors.get_day_list(stand_ym)  # ex) {'1':'목', '2':'금', ..., '31':'토'}

    # 직원별 근로계약 컬럼을 참조하기 위해 day_list를 요일의 영문값으로 세팅
    week_dict = context_processors.day_of_the_week  # {'mon': '월', 'tue': '화', 'wed': '수', 'thu': '목', 'fri': '금', 'sat': '토', 'sun': '일', }
    day_list_eng = {}
    for key, value in day_list.items():
        day_list_eng[key] = list(week_dict.keys())[list(week_dict.values()).index(value)]

    # 기준이 되는 최종 일요일(이번달 말일이 일요일인 경우 or 다음달 첫 일요일) 날짜를 지정 -> 해당 날짜 기준으로 대상 직원 추출
    schedule_date = stand_ym + list(day_list)[-1]
    last_day_weekday = context_processors.get_weekday(schedule_date)

    # 말일이 일요일인 경우에 아예 해당 변수를 만들지 않으면 context에서 오류가 발생하므로, 전달할 변수는 일단 모두 초기화
    next_ym = None
    next_day_list = None
    next_holiday_list = None

    # last_day_weekday가 6(일요일)이면 stand_ym 기준 말일이 기준일자
    # last_day_weekday가 6(일요일)이 아니면, next_ym 기준 첫 일요일이 기준일자
    if last_day_weekday != 6:
        # 다음달 년월을 산출하고, 첫째 일요일인 날짜(6-last_day_weekday)를 붙여서 schedule_date를 재정의
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]
        schedule_date = next_ym + str(6 - last_day_weekday).zfill(2)

    # stand_ym 대상 직원을 추출하여 user_list에 저장
    query_user = f'''
        SELECT u.id, u.emp_name, u.dept, u.position,
                DATE_FORMAT(u.join_date, '%Y%m%d') join_date, DATE_FORMAT(u.out_date, '%Y%m%d') out_date,
                d.order as do, p.order as po
        FROM common_user u
            LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name)
            LEFT OUTER JOIN common_position p on (u.position = p.position_name)
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

    # 공휴일 날짜만 추출하여 list로 만듬. ex) [1, 9, 10, 11]
    holiday_list = list(Holiday.objects.filter(holiday__year=stand_ym[0:4], holiday__month=stand_ym[4:6]).annotate(
        day=ExtractDay('holiday')).values_list('day', flat=True))

    # 공휴일은 OFF 모듈로 지정하기 위해 OFF 모듈의 ID 추출
    off_module_list = list(Module.objects.filter(cat='OFF').values_list('id', flat=True))
    off_module_id = (off_module_list[0] if off_module_list else None)

    # 부서간 구분선 표기를 위해 직전 직원의 부서명을 저장할 변수 설정
    pre_dept = None

    # 기존 스케쥴이 입력되어 있는 user_id를 가져옴
    schedule_user_list = list(
        Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6]).values_list('user_id', flat=True))

    # 스케쥴을 가져옴
    schedule_origin = Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6])

    # user_list에 일자별 근무모듈을 매핑
    for user in user_list:
        # 기존 스케쥴이 있는 경우 schedule에서 가져옴
        if user['id'] in schedule_user_list:
            user['is_new'] = False
            for key, value in day_list_eng.items():
                user[key] = list(schedule_origin.filter(user_id=user['id']).values_list('d' + key + '_id', flat=True))[0]
                # None일 경우는 2가지 케이스(계약이 없거나, 전달에 next_ym으로 입력한 경우)인데, 후자의 경우를 위해 근로계약에서 가져옴
                if user[key] is None:
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

        # 기존 스케쥴이 없는 경우 공휴일 세팅 및 contract에서 가져옴
        else:
            user['is_new'] = True
            for key, value in day_list_eng.items():
                # 입사 전이나, 최종근무일 후라면 None으로 세팅
                if stand_ym + key.zfill(2) < user['join_date'] or (
                        user['out_date'] is not None and stand_ym + key.zfill(2) > user['out_date']):
                    user[key] = None
                # 공휴일이면 OFF 모듈로 세팅
                elif int(key) in holiday_list:
                    user[key] = off_module_id
                else:
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

        # 다음달 일요일까지 날짜를 추가하기 위한 로직
        # 1.마지막날의 요일값을 확인(6-요일값 만큼의 일자가 있음) 2.해당 날짜들로 구성된 day_list 작성
        # 3.next_ym 기준 공휴일 list 생성 4.user_list에 next_ym 기준 스케쥴 추가
        # last_day_weekday가 6(일요일)이면 패스
        if last_day_weekday != 6:
            next_day_list = context_processors.get_day_list(next_ym, 6 - last_day_weekday)
            next_day_list_eng = {}
            for key, value in next_day_list.items():
                next_day_list_eng[key] = list(week_dict.keys())[list(week_dict.values()).index(value)]
            next_holiday_list = list(
                Holiday.objects.filter(holiday__year=next_ym[0:4], holiday__month=next_ym[4:6]).annotate(
                    day=ExtractDay('holiday')).values_list('day', flat=True))

            # 기존 스케쥴이 입력되어 있는 user_id를 가져옴
            next_schedule_user_list = list(
                Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6]).values_list('user_id', flat=True))

            # 스케쥴을 가져옴
            next_schedule_origin = Schedule.objects.filter(year=next_ym[0:4], month=next_ym[4:6])

            # user_list에 일자별 근무모듈을 매핑
            for user in user_list:
                # 기존 스케쥴이 있는 경우 schedule에서 가져옴
                if user['id'] in next_schedule_user_list:
                    for key, value in next_day_list.items():
                        user["n" + key] = \
                        list(next_schedule_origin.filter(user_id=user['id']).values_list('d' + key + '_id', flat=True))[0]
                # 기존 스케쥴이 없는 경우 공휴일 세팅 및 contract에서 가져옴
                else:
                    for key, value in next_day_list_eng.items():
                        # 입사 전이나, 최종근무일 후라면 None으로 세팅
                        if next_ym + key.zfill(2) < user['join_date'] or (
                                user['out_date'] is not None and next_ym + key.zfill(2) > user['out_date']):
                            user["n" + key] = None
                        # 공휴일이면 OFF 모듈로 세팅
                        elif int(key) in next_holiday_list:
                            user["n" + key] = off_module_id
                        else:
                            query = f'''
                                    SELECT c.val
                                    FROM
                                    (
                                    SELECT row_number() over (order by stand_date desc) as rownum , wtm_contract.{value}_id as val
                                    FROM wtm_contract
                                    WHERE user_id = {user['id']}
                                      and DATE_FORMAT(stand_date, '%Y%m%d') <= '{next_ym + key.zfill(2)}'
                                    ) c
                                    WHERE rownum = 1
                                    '''
                            with connection.cursor() as cursor:
                                cursor.execute(query)
                                r = cursor.fetchone()

                            user["n" + key] = (None if r == None else r[0])

    module_list = Module.objects.all()  # 근로모듈을 입력하기 위함
    context = {'stand_ym': stand_ym, 'day_list': day_list, 'user_list': user_list, 'module_list': module_list,
               'holiday_list': holiday_list, 'next_day_list': next_day_list, 'next_holiday_list': next_holiday_list,
               'next_ym': next_ym}
    return render(request, 'wtm/work_schedule_reg.html', context)


@login_required(login_url='common:login')
def work_schedule_delete(request, stand_ym):
    schedule = Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6])
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)
    try:
        schedule.delete()
    except Exception as e:
        messages.error(request, f'데이터베이스 오류가 발생했습니다. {e}')
        redirect('wtm:work_schedule_reg', stand_ym=stand_ym)

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


@login_required(login_url='common:login')
def work_meal(request, stand_year=None):
    if stand_year is None:
        stand_year = datetime.today().year

    # 해당년도의 월일 조합을 list로 생성
    md_list = []
    for i in range(1, 13):
        temp = context_processors.get_day_list(str(stand_year) + str(i).zfill(2))

        for key, value in temp.items():
            md_list.append(str(i).zfill(2) + key.zfill(2))

    # 엑셀에서 활용하기 위해 리스트를 고정시키고자 함. 따라서 0229를 무조건 포함시켜줌
    if '0229' not in md_list:
        md_list.insert(59, '0229')

    # 대상 직원을 추출하여 user_list에 저장
    query_user = f'''
        SELECT u.id, u.emp_name, u.dept, u.position,
                DATE_FORMAT(u.join_date, '%Y%m%d') join_date, DATE_FORMAT(u.out_date, '%Y%m%d') out_date,
                d.order as do, p.order as po
        FROM common_user u
            LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name)
            LEFT OUTER JOIN common_position p on (u.position = p.position_name)
        WHERE is_superuser = false 
            and DATE_FORMAT(u.join_date, '%Y%m%d') <= '{str(stand_year) + "1231"}'
            and (DATE_FORMAT(u.out_date, '%Y%m%d') is null or DATE_FORMAT(u.out_date, '%Y%m%d') >= '{str(stand_year) + "0101"}')
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

    for user in user_list:
        for md in md_list:
            query = f'''
                SELECT IFNULL(
                    HOUR( 
                    TIMEDIFF(
                    TIMEDIFF( 
                    TIMEDIFF(replace(end_time, '-', '00:00:00'), replace(start_time, '-', '00:00:00')),
                    TIMEDIFF(replace(rest1_end_time, '-', '00:00:00'), replace(rest1_start_time, '-', '00:00:00')) ),
                    TIMEDIFF(replace(rest2_end_time, '-', '00:00:00'), replace(rest2_start_time, '-', '00:00:00')) ) ) * 60
                    +
                    MINUTE( 
                    TIMEDIFF(
                    TIMEDIFF( 
                    TIMEDIFF(replace(end_time, '-', '00:00:00'), replace(start_time, '-', '00:00:00')),
                    TIMEDIFF(replace(rest1_end_time, '-', '00:00:00'), replace(rest1_start_time, '-', '00:00:00')) ),
                    TIMEDIFF(replace(rest2_end_time, '-', '00:00:00'), replace(rest2_start_time, '-', '00:00:00')) ) )
                    , 0) as work_time
                FROM wtm_module 
                WHERE id = 
                    (SELECT d{md[2:4].strip("0")}_id
                    FROM wtm_schedule
                    WHERE user_id = {user['id']}
                      and year = '{stand_year}'
                      and month = '{md[0:2]}')
                '''
            with connection.cursor() as cursor:
                cursor.execute(query)
                r = cursor.fetchone()

            user[md] = (0 if r == None else r[0])

    # TODO : 출퇴근 기록 이후에 재개발 필요 -> 어제까지는 출퇴근대로, 오늘이후는 근무표대로

    context = {'md_list': md_list, 'user_list': user_list}
    return render(request, 'wtm/work_meal.html', context)