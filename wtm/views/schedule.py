from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models.functions import ExtractDay
from django.db import connection, transaction
from django.utils import timezone
from datetime import datetime

from common.models import User, Holiday
from common import context_processors
from ..models import Module, Schedule
from .helpers import build_contracts_by_user, get_contract_module_id


def work_schedule(request, stand_ym=None):
    # 기준년월 값이 없으면 현재로 세팅
    if stand_ym is None:
        stand_ym = str(datetime.today().year) + str(datetime.today().month).zfill(2)

    # stand_ym 기준 스케쥴이 없으면 패스
    if Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6]).count() == 0:
        return render(request, 'wtm/work_schedule.html', {'stand_ym': stand_ym})

    day_list = context_processors.get_day_list(stand_ym)  # ex) {'1':'목', '2':'금', ..., '31':'토'}

    # 공휴일 날짜만 추출하여 list로 만듬. ex) [1, 9, 10, 11]
    holiday_list = list(
        Holiday.objects.filter(holiday__year=stand_ym[0:4], holiday__month=stand_ym[4:6])
        .annotate(day=ExtractDay('holiday'))
        .values_list('day', flat=True)
    )

    # 기준이 되는 최종 일요일(이번달 말일이 일요일인 경우 or 다음달 첫 일요일) 날짜를 지정 -> 해당 날짜 기준으로 대상 직원 추출
    schedule_date = stand_ym + list(day_list)[-1]
    last_day_weekday = context_processors.get_days(schedule_date)

    # 말일이 일요일인 경우에 아예 해당 변수를 만들지 않으면 context에서 오류가 발생하므로, 전달할 변수는 일단 모두 초기화
    next_ym = None
    next_day_list = None
    next_holiday_list = None

    # last_day_weekday가 6(일요일)이면 stand_ym 기준 말일이 기준일자
    # last_day_weekday가 6(일요일)이 아니면, next_ym 기준 첫 일요일이 기준일자
    if last_day_weekday != 6:
        # 다음달 년월을 산출하고, 첫째 일요일인 날짜(6-last_day_weekday)를 붙여서 schedule_date를 재정의
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]
        next_day_list = context_processors.get_day_list(next_ym, 6 - last_day_weekday)
        next_holiday_list = list(
            Holiday.objects.filter(holiday__year=next_ym[0:4], holiday__month=next_ym[4:6])
            .annotate(day=ExtractDay('holiday'))
            .values_list('day', flat=True)
        )
        schedule_date = next_ym + str(6 - last_day_weekday).zfill(2)

    # 대상 직원을 추출하여 schedule_list에 저장 (기존 raw 유지)
    query_user = f'''
            SELECT u.id, u.emp_name, u.dept, u.position,
                    DATE_FORMAT(u.join_date, '%Y%m%d') join_date, DATE_FORMAT(u.out_date, '%Y%m%d') out_date,
                    d.`order` as do, p.`order` as po
            FROM common_user u
                LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name)
                LEFT OUTER JOIN common_position p on (u.position = p.position_name)
            WHERE is_employee = TRUE
                and DATE_FORMAT(u.join_date, '%Y%m%d') <= '{schedule_date}'
                and (DATE_FORMAT(u.out_date, '%Y%m%d') is null or DATE_FORMAT(u.out_date, '%Y%m%d') >= '{stand_ym + '01'}')
            ORDER BY do, po, join_date
            '''

    with connection.cursor() as cursor:
        cursor.execute(query_user)
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

    # 이번달 / 다음달 스케줄을 한 번에 가져와서 user_id별로 묶기
    user_ids = [row["id"] for row in schedule_list]

    # 이번달 스케줄
    schedules_qs = Schedule.objects.filter(
        year=stand_ym[0:4],
        month=stand_ym[4:6],
        user_id__in=user_ids,
    )
    schedule_map = {s.user_id: s for s in schedules_qs}

    # 다음달 스케줄 (말일이 일요일이 아닐 때만)
    next_schedule_map = {}
    if next_ym is not None:
        next_schedules_qs = Schedule.objects.filter(
            year=next_ym[0:4],
            month=next_ym[4:6],
            user_id__in=user_ids,
        )
        next_schedule_map = {s.user_id: s for s in next_schedules_qs}

    # 모듈 전체를 한 번에 가져와서 "id,cat,name,start,end,color" 문자열로 매핑
    module_list = list(Module.objects.all())  # 나중에 context에도 그대로 사용
    module_str_map = {}
    for m in module_list:
        module_str_map[m.id] = f"{m.id},{m.cat},{m.name},{m.start_time},{m.end_time},{m.color}"

    # 부서간 구분선 표기를 위해 직전 직원의 부서명을 저장할 변수 설정
    pre_dept = None

    # 직원별로 일자별 근무모듈을 매핑
    for row in schedule_list:
        uid = row["id"]

        # 이번달 스케줄 row (있으면)
        sched = schedule_map.get(uid)
        if sched is not None:
            # d1 ~ d31
            for i in range(1, 32):
                module_id = getattr(sched, f"d{i}_id", None)
                row[f"d{i}"] = module_str_map.get(module_id) if module_id else None

        # 다음달 n1 ~ n6 (다음달 스케줄이 있고, next_ym이 있는 경우만)
        if next_ym is not None:
            next_sched = next_schedule_map.get(uid)
            if next_sched is not None:
                for i in range(1, 7):
                    module_id = getattr(next_sched, f"d{i}_id", None)
                    row[f"n{i}"] = module_str_map.get(module_id) if module_id else None

        # 직전 직원의 부서명과 비교해서 같으면 'N'을 다르면 'Y' 세팅 (기존 로직 그대로)
        row['dept_diff'] = ('N' if pre_dept == row['dept'] else 'Y')
        pre_dept = row['dept']

    # 근무표와 직원현황이 다른 경우 1 : 스케쥴 작성 이후 추가된 직원이 있는 경우 (user minus schedule)
    raw_query = f'''
        SELECT u.emp_name
        FROM common_user u
        WHERE u.is_employee = TRUE
          -- 해당 월에 단 하루라도 재직한 사람
          AND DATE_FORMAT(u.join_date, '%Y%m%d') <= '{stand_ym + list(day_list)[-1]}'
          AND (
                u.out_date IS NULL
                OR DATE_FORMAT(u.out_date, '%Y%m%d') >= '{stand_ym + '01'}'
              )
          -- 그 달 스케쥴이 1건도 없는 경우
          AND NOT EXISTS (
                SELECT 1
                FROM wtm_schedule s
                WHERE s.user_id = u.id
                  AND s.year  = '{stand_ym[0:4]}'
                  AND s.month = '{stand_ym[4:6]}'
          )
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
        SELECT DISTINCT u.emp_name
        FROM wtm_schedule s
        JOIN common_user u ON s.user_id = u.id
        WHERE u.is_employee = TRUE
          AND s.year  = '{stand_ym[0:4]}'
          AND s.month = '{stand_ym[4:6]}'
          -- "그 달 직원" 조건에 해당하지 않는 사람만
          AND NOT (
                DATE_FORMAT(u.join_date, '%Y%m%d') <= '{stand_ym + list(day_list)[-1]}'
            AND (
                  u.out_date IS NULL
                  OR DATE_FORMAT(u.out_date, '%Y%m%d') >= '{stand_ym + '01'}'
                )
          )
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

    context = {
        'schedule_list': schedule_list,
        'stand_ym': stand_ym,
        'day_list': day_list,
        'holiday_list': holiday_list,
        'next_ym': next_ym,
        'next_day_list': next_day_list,
        'next_holiday_list': next_holiday_list,
        'module_list': module_list,  # 위에서 만든 list 재사용
    }
    return render(request, 'wtm/work_schedule.html', context)


@login_required(login_url='common:login')
def work_schedule_reg(request, stand_ym):
    if request.method == 'POST':
        # -----------------------------
        # 1. POST 데이터 파싱
        #    sch_{user_id}_{day} → user별 row(dict) 구성
        #    값은 Module 객체 대신 "모듈 id(int)"만 저장
        # -----------------------------
        def empty_row(user_id: int | None = None):
            base = {f'd{i}': None for i in range(1, 32)}  # d1 ~ d31
            base.update({f'n{i}': None for i in range(1, 7)})  # n1 ~ n6
            base['user_id'] = user_id
            return base

        rows_by_user: dict[int, dict] = {}

        for key, value in request.POST.items():
            if not key.startswith('sch_'):
                continue

            # key 형식: sch_{user_id}_{day}
            # 예: sch_15_1, sch_15_31, sch_15_n1 ...
            _, user_id_str, day_key = key.split('_', 2)
            user_id = int(user_id_str)

            row = rows_by_user.get(user_id)
            if row is None:
                row = empty_row(user_id)
                rows_by_user[user_id] = row

            module_id = int(value) if value else None

            if day_key.startswith('n'):
                # n1 ~ n6
                row[day_key] = module_id
            else:
                # 이번달은 d1 ~ d31 로 매핑
                row[f'd{day_key}'] = module_id

        schedule_list = list(rows_by_user.values())

        # POST로 넘어온 게 없으면 바로 목록으로
        if not schedule_list:
            return redirect('wtm:work_schedule', stand_ym=stand_ym)

        # -----------------------------
        # 2. 기존 스케줄 중복 체크 (기존 로직 유지)
        # -----------------------------
        existing_users_this_month = set(
            Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6])
            .values_list('user_id', flat=True)
        )

        post_user_ids = {row['user_id'] for row in schedule_list}
        duplicated_users = existing_users_this_month & post_user_ids

        # 기존 코드: 한 명이라도 있으면 '중복된 스케쥴입니다.' 찍고 바로 work_schedule로
        if duplicated_users:
            messages.error(request, '중복된 스케쥴입니다.')
            return redirect('wtm:work_schedule', stand_ym=stand_ym)

        # -----------------------------
        # 3. 공통 날짜 정보 (말일/요일/다음달 등)
        # -----------------------------
        # 예: stand_ym = '202512' → '20251231' 같은 형태
        schedule_date = stand_ym + str(context_processors.get_last_day(stand_ym))
        last_day_weekday = context_processors.get_days(schedule_date)  # 0=월 ~ 6=일
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]  # 다음달 'YYYYMM'
        last_day_of_month = int(schedule_date[6:8])  # 말일(28/29/30/31)

        # -----------------------------
        # 4. User / 다음달 Schedule 한 번에 로딩
        # -----------------------------
        users = User.objects.in_bulk(post_user_ids)  # {id: User}

        next_schedule_map: dict[int, Schedule] = {}
        days_to_copy = 0
        if last_day_weekday != 6:
            # 다음달 스케줄은 d1 ~ d(일요일까지)만 사용
            days_to_copy = 6 - last_day_weekday
            next_qs = Schedule.objects.filter(
                year=next_ym[0:4],
                month=next_ym[4:6],
                user_id__in=post_user_ids,
            )
            next_schedule_map = {s.user_id: s for s in next_qs}

        now = timezone.now()

        # -----------------------------
        # 5. 트랜잭션 내에서 이번달 + 다음달 저장
        # -----------------------------
        with transaction.atomic():
            for row in schedule_list:
                user_id = row['user_id']
                user = users.get(user_id)
                if user is None:
                    # 방어 코드: 이론상 없어야 함
                    continue

                # 5-1. 이번달 스케줄 insert
                # 직원의 입사일이 stand_ym의 말일보다 크면, stand_ym 기준 스케쥴은 없으므로 패스
                if stand_ym < user.join_date.strftime('%Y%m'):
                    pass
                else:
                    obj1 = Schedule(
                        user_id=user_id,
                        year=stand_ym[0:4],
                        month=stand_ym[4:6],
                        reg_id=request.user,
                        reg_date=now,
                        mod_id=request.user,
                        mod_date=now,
                    )

                    # d1 ~ d(말일) 까지만 세팅 (FK id 필드에 직접 모듈 id를 넣음)
                    for i in range(1, last_day_of_month + 1):
                        module_id = row.get(f'd{i}')
                        setattr(obj1, f'd{i}_id', module_id)

                    obj1.save()

                # 5-2. 다음달 (첫 일요일까지) 처리
                # 말일이 일요일이 아니면 다음달 일요일까지 입력
                if last_day_weekday != 6:
                    # 직원의 최종근무일이 next_ym의 1일보다 작으면, next_ym 기준 스케쥴은 없음
                    if user.out_date is not None and user.out_date.strftime('%Y%m') < next_ym:
                        continue

                    obj2 = next_schedule_map.get(user_id)
                    if obj2 is not None:
                        # 기존 스케줄 update
                        obj2.mod_id = request.user
                        obj2.mod_date = now
                    else:
                        # 새 스케줄 insert
                        obj2 = Schedule(
                            user_id=user_id,
                            year=next_ym[0:4],
                            month=next_ym[4:6],
                            reg_id=request.user,
                            reg_date=now,
                            mod_id=request.user,
                            mod_date=now,
                        )
                        next_schedule_map[user_id] = obj2

                    # d1 ~ d{days_to_copy} ← n1 ~ n{days_to_copy}
                    for i in range(1, days_to_copy + 1):
                        module_id = row.get(f'n{i}')
                        setattr(obj2, f'd{i}_id', module_id)

                    obj2.save()

        messages.success(request, '근무표가 등록되었습니다.')

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
    last_day_weekday = context_processors.get_days(schedule_date)

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
        WHERE is_employee = TRUE
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

    # 직원별 계약 정보를 한 번에 불러와서 메모리에 적재
    contracts_by_user = build_contracts_by_user(user_list, schedule_date)

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
                # 미리 불러온 계약 정보에서 찾기
                contracts = contracts_by_user.get(user["id"])
                if not contracts:
                    user[key] = None
                else:
                    target_date = datetime.strptime(stand_ym + key.zfill(2), "%Y%m%d").date()
                    user[key] = get_contract_module_id(contracts, target_date, value)

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
                        contracts = contracts_by_user.get(user["id"])
                        if not contracts:
                            user["n" + key] = None
                        else:
                            target_date = datetime.strptime(next_ym + key.zfill(2), "%Y%m%d").date()
                            user["n" + key] = get_contract_module_id(contracts, target_date, value)

    module_list = Module.objects.all()  # 근로모듈을 입력하기 위함

    context = {'stand_ym': stand_ym, 'day_list': day_list, 'user_list': user_list, 'module_list': module_list,
               'holiday_list': holiday_list, 'next_day_list': next_day_list, 'next_holiday_list': next_holiday_list,
               'next_ym': next_ym}
    return render(request, 'wtm/work_schedule_reg.html', context)


@login_required(login_url='common:login')
def work_schedule_modify(request, stand_ym):
    if request.method == 'POST':
        # -----------------------------
        # 1. POST 데이터 파싱
        #    sch_{user_id}_{day}  → user별 row(dict)로 정리
        #    값은 Module 인스턴스 대신 "모듈 id(int)"만 저장
        # -----------------------------
        # day 필드 초기 템플릿
        def empty_row(user_id: int | None = None):
            base = {f'd{i}': None for i in range(1, 32)}
            base.update({f'n{i}': None for i in range(1, 7)})
            base['user_id'] = user_id
            return base

        rows_by_user: dict[int, dict] = {}

        for key, value in request.POST.items():
            if not key.startswith('sch_'):
                continue

            # key 형식: sch_{user_id}_{day}  (day: '1'~'31' 또는 'n1'~'n6')
            _, user_id_str, day_key = key.split('_', 2)
            user_id = int(user_id_str)

            row = rows_by_user.get(user_id)
            if row is None:
                row = empty_row(user_id)
                rows_by_user[user_id] = row

            module_id = int(value) if value else None

            if day_key.startswith('n'):
                # n1 ~ n6 그대로 사용
                row[day_key] = module_id
            else:
                # 이번달은 d1 ~ d31 으로 매핑
                row[f'd{day_key}'] = module_id

        # dict → list 로 변환 (기존 schedule_list와 동일한 역할)
        schedule_list = list(rows_by_user.values())

        # -----------------------------
        # 2. 공통 변수/정보 계산
        # -----------------------------
        # stand_ym 기준 기존 스케쥴이 입력되어 있는 user_id 전체 (삭제용)
        existing_users_this_month = set(
            Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6])
            .values_list('user_id', flat=True)
        )

        # 이번 POST에서 넘어온 user_id
        post_user_ids = {row['user_id'] for row in schedule_list}

        # 삭제 대상: 기존에는 있었는데, 이번 POST에는 없는 유저
        users_to_delete = existing_users_this_month - post_user_ids

        # 다음달 관련 계산
        schedule_date = stand_ym + str(context_processors.get_last_day(stand_ym))
        last_day_weekday = context_processors.get_days(schedule_date)
        next_ym = context_processors.get_month(stand_ym, 1)[0:6]

        # 한 달의 마지막 일자 (1~말일 d필드만 사용)
        last_day_of_month = int(schedule_date[6:8])

        # -----------------------------
        # 3. 한 번에 필요한 User / Schedule 미리 로딩
        # -----------------------------
        from django.db import transaction

        with transaction.atomic():
            # (1) 이번달 스케쥴 삭제 (삭제 대상만 bulk delete)
            if users_to_delete:
                Schedule.objects.filter(
                    year=stand_ym[0:4],
                    month=stand_ym[4:6],
                    user_id__in=users_to_delete,
                ).delete()

            # (2) 이번 POST에 포함된 직원 정보 / 스케쥴 미리 로딩
            #     - User: join_date / out_date 비교용
            #     - Schedule: 수정/삽입용 (select_for_update 로 락 걸어도 좋음)
            users = User.objects.in_bulk(post_user_ids)  # {id: User}

            current_qs = Schedule.objects.filter(
                year=stand_ym[0:4],
                month=stand_ym[4:6],
                user_id__in=post_user_ids,
            )
            current_map = {s.user_id: s for s in current_qs}  # {user_id: Schedule}

            # (3) 다음달 스케쥴도 미리 로딩 (말일이 일요일이 아닐 때만)
            next_map: dict[int, Schedule] = {}
            if last_day_weekday != 6:
                next_qs = Schedule.objects.filter(
                    year=next_ym[0:4],
                    month=next_ym[4:6],
                    user_id__in=post_user_ids,
                )
                next_map = {s.user_id: s for s in next_qs}

            now = timezone.now()

            # -----------------------------
            # 4. 이번달 스케쥴 저장/수정
            # -----------------------------
            for row in schedule_list:
                user_id = row['user_id']
                user = users.get(user_id)
                if user is None:
                    # 이론상 없어야 하지만, 방어적으로
                    continue

                # 기존 스케쥴이 존재하는 경우: update
                obj = current_map.get(user_id)
                if obj is not None:
                    obj.mod_id = request.user
                    obj.mod_date = now
                else:
                    # 기존 스케쥴이 없는 경우 insert
                    # 직원의 입사일이 stand_ym의 말일보다 크면, stand_ym 기준 스케쥴은 없으므로 패스
                    if stand_ym < user.join_date.strftime('%Y%m'):
                        obj = None
                    else:
                        obj = Schedule(
                            user_id=user_id,
                            year=stand_ym[0:4],
                            month=stand_ym[4:6],
                            reg_id=request.user,
                            reg_date=now,
                            mod_id=request.user,
                            mod_date=now,
                        )
                        current_map[user_id] = obj

                # 실제 d1~d(말일) 값 세팅
                if obj is not None:
                    for i in range(1, last_day_of_month + 1):
                        module_id = row.get(f'd{i}')
                        # FK: d{i}_id 에 직접 id 세팅
                        setattr(obj, f'd{i}_id', module_id)
                    obj.save()

            # -----------------------------
            # 5. 다음달(첫 일요일까지) 스케쥴 저장/수정
            # -----------------------------
            if last_day_weekday != 6:
                days_to_copy = 6 - last_day_weekday  # n1 ~ n{days_to_copy} 사용

                for row in schedule_list:
                    user_id = row['user_id']
                    user = users.get(user_id)
                    if user is None:
                        continue

                    # 직원의 최종근무일이 next_ym의 1일보다 작으면, next_ym 기준 스케쥴은 없으므로 패스
                    if user.out_date is not None and user.out_date.strftime('%Y%m') < next_ym:
                        continue

                    obj2 = next_map.get(user_id)
                    if obj2 is not None:
                        # 기존 스케쥴이 존재하는 경우: update
                        obj2.mod_id = request.user
                        obj2.mod_date = now
                    else:
                        # 기존 스케쥴이 없는 경우: insert
                        obj2 = Schedule(
                            user_id=user_id,
                            year=next_ym[0:4],
                            month=next_ym[4:6],
                            reg_id=request.user,
                            reg_date=now,
                            mod_id=request.user,
                            mod_date=now,
                        )
                        next_map[user_id] = obj2

                    # d1 ~ d{days_to_copy} ← n1 ~ n{days_to_copy} 매핑
                    for i in range(1, days_to_copy + 1):
                        module_id = row.get(f'n{i}')
                        setattr(obj2, f'd{i}_id', module_id)

                    obj2.save()

        messages.success(request, '근무표가 수정되었습니다.')

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
    last_day_weekday = context_processors.get_days(schedule_date)

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

    # 1) stand_ym 대상 직원을 추출하여 user_list에 저장
    query_user = f'''
        SELECT u.id, u.emp_name, u.dept, u.position,
                DATE_FORMAT(u.join_date, '%Y%m%d') join_date, DATE_FORMAT(u.out_date, '%Y%m%d') out_date,
                d.order as do, p.order as po
        FROM common_user u
            LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name)
            LEFT OUTER JOIN common_position p on (u.position = p.position_name)
        WHERE is_employee = TRUE
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

    # 2) 공휴일, OFF 모듈
    # 공휴일 날짜만 추출하여 list로 만듬. ex) [1, 9, 10, 11]
    holiday_list = list(Holiday.objects.filter(holiday__year=stand_ym[0:4], holiday__month=stand_ym[4:6]).annotate(
        day=ExtractDay('holiday')).values_list('day', flat=True))

    # 공휴일은 OFF 모듈로 지정하기 위해 OFF 모듈의 ID 추출
    off_module_list = list(Module.objects.filter(cat='OFF').values_list('id', flat=True))
    off_module_id = (off_module_list[0] if off_module_list else None)

    # 3) 이번달 스케줄 전체, dict로 매핑
    schedule_origin = Schedule.objects.filter(year=stand_ym[0:4], month=stand_ym[4:6]).select_related()
    schedule_user_list = list(schedule_origin.values_list('user_id', flat=True))
    schedule_map = {s.user_id: s for s in schedule_origin}

    # 4) 다음달(필요시) 스케줄 전체, dict로 매핑 + 공휴일
    next_schedule_map = {}
    next_schedule_user_list = []
    if last_day_weekday != 6:
        next_day_list = context_processors.get_day_list(next_ym, 6 - last_day_weekday)
        next_day_list_eng = {}
        for key, value in next_day_list.items():
            next_day_list_eng[key] = list(week_dict.keys())[list(week_dict.values()).index(value)]

        next_holiday_list = list(
            Holiday.objects
            .filter(holiday__year=next_ym[0:4], holiday__month=next_ym[4:6])
            .annotate(day=ExtractDay('holiday'))
            .values_list('day', flat=True)
        )

        next_schedule_origin = Schedule.objects.filter(
            year=next_ym[0:4], month=next_ym[4:6]
        ).select_related()
        next_schedule_user_list = list(next_schedule_origin.values_list('user_id', flat=True))
        next_schedule_map = {s.user_id: s for s in next_schedule_origin}

    # 5) 계약 전체를 한 번에 불러와 user별로 매핑
    # schedule_date는 위에서 '기준 마지막 일자(이번달 말 or 다음달 첫 일요일)'로 세팅해 둠
    contracts_by_user = build_contracts_by_user(user_list, schedule_date)

    # 부서간 구분선 표기를 위해 직전 직원의 부서명을 저장할 변수 설정
    pre_dept = None

    # user_list에 일자별 근무모듈을 매핑
    for user in user_list:
        # 기존 스케쥴이 있는 경우 schedule에서 가져옴
        if user['id'] in schedule_user_list:
            user['is_new'] = False
            for key, value in day_list_eng.items():
                user[key] = list(schedule_origin.filter(user_id=user['id']).values_list('d' + key + '_id', flat=True))[0]
                # None일 경우는 2가지 케이스(계약이 없거나, 전달에 next_ym으로 입력한 경우)인데, 후자의 경우를 위해 근로계약에서 가져옴
                if user[key] is None:
                    if int(key) in holiday_list:
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

        # 기존 스케쥴이 없는 경우 공휴일 세팅 및 contract에서 가져옴달
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
        return redirect('wtm:work_schedule_reg', stand_ym=stand_ym)

    messages.success(request, '근무표가 삭제되었습니다.')

    return redirect('wtm:work_schedule', stand_ym=stand_ym)


@login_required(login_url='common:login')
def work_schedule_popup(request):
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)

    if request.method == 'POST':
        new_user_id = request.POST.get("user_id")
        new_stand_date = request.POST.get("stand_date")
        new_module_id = request.POST.get("module_id")
        column = f'd{str(int(new_stand_date[6:8]))}_id'

        user = User.objects.get(pk=new_user_id)

        try:
            obj = Schedule.objects.filter(year=new_stand_date[0:4], month=new_stand_date[4:6],
                                          user_id=new_user_id)

            obj_to_update = obj[0]

            # 날짜에 해당하는 컬럼을 변경하기 위해 setattr() 사용
            setattr(obj_to_update, column, new_module_id)
            obj_to_update.mod_id = request.user
            obj_to_update.mod_date = timezone.now()

            obj_to_update.save()

            messages.success(request, f'[{user.position} {user.emp_name}({user.dept}), {new_stand_date[0:4]}-{new_stand_date[4:6]}-{new_stand_date[6:8]}] 근무표가 수정되었습니다.')
        except Exception as e:
            messages.warning(request, f'데이터베이스 오류가 발생했습니다. {e}')

        # 어느 화면을 통해서 요청이 왔는지에 따라 리다이렉트 분기
        from_index = request.POST.get("from_index") == "1"

        if from_index:
            # Today 화면으로
            return redirect('wtm:index', new_stand_date)
        else:
            # 근무표 화면으로
            return redirect('wtm:work_schedule', new_stand_date[0:6])