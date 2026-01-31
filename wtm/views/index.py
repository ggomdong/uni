from datetime import datetime, date

from django.utils import timezone
from django.shortcuts import render
from django.contrib import messages
from django.db import connection

from common import context_processors
from wtm.services.attendance import build_daily_attendance_for_users
from .helpers import dictfetchall
from ..models import Module


def index(request, stand_day=None):
    if stand_day is None:
        stand_day = datetime.today().strftime('%Y%m%d')

    days = context_processors.get_days_korean(stand_day)
    branch = request.user.branch

    day_num = int(stand_day[6:8])
    if not 1 <= day_num <= 31:
        raise ValueError("invalid day")

    day_col = f"d{day_num}_id"  # 여기만 문자열 조립(식별자)

    user_list = []
    max_workers = 0
    work_list = []

    ###### 1. 근무인원 현황 (화면 상단) ######

    query = f'''
        SELECT u.dept, u.position, u.emp_name,
            m.start_time, m.end_time,
            case when STR_TO_DATE(m.start_time, '%%H:%%i') <= STR_TO_DATE('13:00', '%%H:%%i') then 1
                else 0
            end as am,
            case when STR_TO_DATE(m.end_time, '%%H:%%i') >= STR_TO_DATE('14:00', '%%H:%%i') then 1
                else 0
            end as pm,
            d.order as do, p.order as po
        FROM common_user u
            LEFT OUTER JOIN wtm_schedule s on (u.id = s.user_id AND s.branch_id = u.branch_id AND s.year = %s AND s.month = %s)
            LEFT OUTER JOIN wtm_module m on (s.{day_col} = m.id AND m.branch_id = u.branch_id)
            LEFT OUTER JOIN common_dept d on (u.dept = d.dept_name AND d.branch_id = u.branch_id)
            LEFT OUTER JOIN common_position p on (u.position = p.position_name AND p.branch_id = u.branch_id)
        WHERE is_employee = TRUE
          and u.branch_id = %s
          and DATE_FORMAT(u.join_date, '%%Y%%m%%d') <= %s
          and (DATE_FORMAT(u.out_date, '%%Y%%m%%d') is null or DATE_FORMAT(u.out_date, '%%Y%%m%%d') >= %s)
        ORDER BY do, po, join_date, emp_name
        '''
    # print(query)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                [stand_day[0:4], stand_day[4:6], branch.id, stand_day, stand_day],
            )
            results = cursor.fetchall()

            x = cursor.description
            user_list = []
            dept = ''
            category = -1
            for r in results:
                # 부서가 달라지면, 새로운 리스트를 추가
                if r[0] != '의사' and dept != r[0]:
                    dept = r[0]
                    category += 1
                    user_list.append([])
                # print(f'dept: {dept}, category: {category}')
                i = 0
                d = {}
                while i < len(x):
                    d[x[i][0]] = r[i]
                    i = i + 1
                user_list[category].append(d)

            # print(user_list)
        i = 0
        max_workers = 0
        for i in range(category+1):
            # TODAY의 테이블 row 크기를 정하기 위해 max 값 계산
            # (틀린 로직) 오전 / 오후 근무인원과 비교하여 당일 최대 근무인원수 계산
            # max_workers = max(max_workers, d['sum_am'], d['sum_pm'])
            # (맞는 로직) 근무인원이 아닌 전체 인원수를 계산
            if max_workers < len(user_list[i]):
                max_workers = len(user_list[i])

            # print(f'max_workers: {max_workers}')

            # 부서별 오전/오후 근무인원 합계를 dict에 추가
            d = {}
            d['sum_am'] = sum(item['am'] for item in user_list[i])
            d['sum_pm'] = sum(item['pm'] for item in user_list[i])

            user_list[i].insert(0, d)

    except Exception as e:
        messages.warning(request, f'오류가 발생했습니다. {e}')

    ###### 2. 근태현황 (화면 하단) ######

    ymd = stand_day if stand_day else timezone.now().strftime("%Y%m%d")
    day = date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))

    # User를 메인으로 Contract를 LEFT OUTER JOIN 하여, 계약이 있는 경우에만 리스트에 보여줌
    # 1. 직원관리 화면과 다르게, 현재(NOW())가 아닌 기준일자 보다 과거인 기준일이 존재하면 max(과거 기준일)
    # 2. 기준일자 보다 과거인 기준일이 없으면 min(미래 기준일)
    # SQL에 조건을 넣기가 애매해서, 1,2를 union한 후 min 값을 얻는 걸로 구현함
    query = f'''
            SELECT u.id as user_id, u.dept, u.position, u.emp_name,
                s.{day_col} as module_id,
                m.cat, m.name, m.start_time, m.end_time, m.rest1_start_time, m.rest1_end_time, m.rest2_start_time, m.rest2_end_time,
                d.order as do, p.order as po
            FROM common_user u
                LEFT OUTER JOIN wtm_schedule s
                             ON u.id = s.user_id
                            AND s.year = %s
                            AND s.month = %s
                            AND s.branch_id = u.branch_id
                LEFT OUTER JOIN wtm_module m
                             ON s.{day_col} = m.id AND m.branch_id = u.branch_id
                LEFT OUTER JOIN (
                    SELECT * FROM wtm_contract WHERE (user_id, stand_date) IN
                    (
                        SELECT a.user_id, MIN(a.stand_date)
                        FROM
                        (
                            SELECT user_id, MAX(stand_date) as stand_date FROM wtm_contract WHERE stand_date <= %s AND branch_id = %s GROUP BY user_id
                            UNION
                            SELECT user_id, MIN(stand_date) as stand_date FROM wtm_contract WHERE stand_date > %s AND branch_id = %s GROUP BY user_id
                            ) a
                            group by a.user_id
                        )
                    AND branch_id = %s
                ) c ON u.id = c.user_id
                LEFT OUTER JOIN common_dept d
                             ON u.dept = d.dept_name AND d.branch_id = u.branch_id
                LEFT OUTER JOIN common_position p
                             ON u.position = p.position_name AND p.branch_id = u.branch_id
            WHERE is_employee = TRUE
              and c.check_yn = 'Y'
              and u.branch_id = %s
              and DATE_FORMAT(u.join_date, '%%Y%%m%%d') <= %s
              and (DATE_FORMAT(u.out_date, '%%Y%%m%%d') is null OR DATE_FORMAT(u.out_date, '%%Y%%m%%d') >= %s)
            ORDER BY do, po, join_date, emp_name
            '''

    try:
        with connection.cursor() as cur:
            cur.execute(
                query,
                [
                    stand_day[0:4],
                    stand_day[4:6],
                    stand_day,
                    branch.id,
                    stand_day,
                    branch.id,
                    branch.id,
                    branch.id,
                    stand_day,
                    stand_day,
                ],
            )
            base_rows = dictfetchall(cur)

        # 계산은 attendance 모듈에 위임
        work_list = build_daily_attendance_for_users(base_rows, day, branch=branch)

    except Exception as e:
        messages.warning(request, f'오류가 발생했습니다. {e}')

    module_list = Module.objects.filter(branch=branch).order_by('order', 'id')  # 근로모듈을 입력하기 위함

    context = {'stand_day': stand_day, 'days': days, 'user_list': user_list, 'work_list': work_list,
               'max_workers': max_workers, 'module_list': module_list}
    return render(request, 'wtm/index.html', context)
