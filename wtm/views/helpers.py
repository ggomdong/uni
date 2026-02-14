from django.db import connection
from datetime import date
from calendar import monthrange

from common.models import Holiday, Business
from wtm.services.base_users import fetch_base_users_for_month as _fetch_base_users_for_month


# 공통: cursor → dict 리스트 변환
def dictfetchall(cur):
    cols = [col[0] for col in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def sec_to_hhmmss(total_seconds: int) -> str:
    """
    초 단위를 'HH:MM:SS' 문자열로 변환
    """
    if not total_seconds:
        return "00:00:00"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def build_contracts_by_user(user_list, schedule_date, *, branch):
    """
    근무표 수정을 위한 헬퍼함수
    wtm_contract에서 기준일자(schedule_date)까지의 계약을 한 번에 읽어서 user_id별로 정리
    반환: { user_id: [ { 'user_id': ..., 'stand_date': date, 'mon_id': ..., ... }, ... ] }
    """
    if not user_list:
        return {}

    user_ids = [str(u['id']) for u in user_list if u.get('id') is not None]
    if not user_ids:
        return {}

    # schedule_date는 'YYYYMMDD' 문자열
    placeholders = ",".join(["%s"] * len(user_ids))
    query = f'''
        SELECT
            id,
            user_id,
            stand_date,
            mon_id,
            tue_id,
            wed_id,
            thu_id,
            fri_id,
            sat_id,
            sun_id
        FROM wtm_contract
        WHERE branch_id = %s
          AND user_id IN ({placeholders})
          AND DATE_FORMAT(stand_date, '%%Y%%m%%d') <= %s
        ORDER BY user_id, stand_date
    '''
    params = [branch.id, *user_ids, schedule_date]

    contracts_by_user: dict[int, list[dict]] = {}

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]

    for row in rows:
        d = dict(zip(cols, row))
        # stand_date를 date 타입으로 통일
        if hasattr(d["stand_date"], "date"):
            d["stand_date"] = d["stand_date"].date()
        contracts_by_user.setdefault(d["user_id"], []).append(d)

    return contracts_by_user


def get_contract_module_id(contracts, target_date, weekday_eng: str):
    """
    근무표 수정을 위한 헬퍼함수
    해당 직원의 계약 리스트(contracts)에서
    target_date 기준으로 가장 최근 stand_date의 weekday_eng(mon/tue/...) 모듈 id를 찾아준다.
    """
    if not contracts:
        return None

    field = f"{weekday_eng}_id"
    latest_val = None

    for c in contracts:
        if c["stand_date"] <= target_date:
            latest_val = c.get(field)
        else:
            # stand_date 오름차순 정렬되어 있으니 여기서 끊어도 됨
            break

    return latest_val


def get_non_business_days(year: int, month: int, *, branch) -> set[int]:
    """
    미영업일(day int) 집합 반환.
    - Holiday(법정 공휴일)
    - Business(요일별 영업/비영업 패턴: mon~sun, 'Y'=영업, 그 외=비영업)
    """
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # 1) 공휴일
    holiday_qs = Holiday.objects.filter(branch=branch, holiday__range=(first_day, last_day))
    holiday_set = set(h.holiday for h in holiday_qs)

    # 2) 비영업 요일 패턴 (가장 최근 stand_date 기준)
    business = (
        Business.objects.filter(branch=branch, stand_date__lte=last_day)
        .order_by("-stand_date")
        .first()
    )

    def is_business_open(d: date) -> bool:
        if business is None:
            return True  # 패턴 없으면 전 요일 영업으로 가정 (view와 동일)
        weekday = d.weekday()  # 0=월..6=일
        code = {
            0: business.mon,
            1: business.tue,
            2: business.wed,
            3: business.thu,
            4: business.fri,
            5: business.sat,
            6: business.sun,
        }[weekday]
        return code == "Y"

    non_business_days: set[int] = set()
    for day in range(1, last_day.day + 1):
        d = date(year, month, day)
        is_holiday = d in holiday_set
        open_flag = is_business_open(d)
        if is_holiday or (not open_flag):
            non_business_days.add(day)

    return non_business_days


def fetch_base_users_for_month(stand_ym: str, *, branch, is_contract_checked: bool = True) -> list[dict]:
    return _fetch_base_users_for_month(
        stand_ym,
        branch=branch,
        is_contract_checked=is_contract_checked,
    )


def fetch_log_users_for_day(stand_day: str, *, branch):
    """
    근태기록-일별상세 화면에서 사용할 '대상 직원 목록'을 RAW SQL로 조회.
    - contract.check_yn = 'Y'
    - 해당 연월에 근무표 존재
    - 재직자
    - 부서/직위 order 순으로 정렬
    """
    # stand_day: 'YYYYMMDD'
    day_no = int(stand_day[6:8])  # 1~31 → s.d{day_no}_id

    query = """
        SELECT
            u.id AS user_id,
            u.emp_name,
            u.dept,
            u.position,
            DATE_FORMAT(u.join_date, '%%Y%%m%%d') AS join_date,
            d.`order` AS dept_order,
            p.`order` AS position_order
        FROM common_user u
            LEFT OUTER JOIN wtm_schedule s
                ON u.id = s.user_id
               AND s.branch_id = u.branch_id
            LEFT OUTER JOIN (
                SELECT *
                  FROM wtm_contract
                 WHERE (user_id, stand_date) IN
                 (
                    SELECT a.user_id, MIN(a.stand_date)
                      FROM (
                            SELECT user_id, MAX(stand_date) AS stand_date
                              FROM wtm_contract
                             WHERE stand_date <= %s AND branch_id = %s
                             GROUP BY user_id
                            UNION
                            SELECT user_id, MIN(stand_date) AS stand_date
                              FROM wtm_contract
                             WHERE stand_date > %s AND branch_id = %s
                             GROUP BY user_id
                           ) a
                     GROUP BY a.user_id
                 )
                 AND branch_id = %s
            ) c
                ON u.id = c.user_id
            LEFT OUTER JOIN common_dept d
                ON u.dept = d.dept_name AND d.branch_id = u.branch_id
            LEFT OUTER JOIN common_position p
                ON u.position = p.position_name AND p.branch_id = u.branch_id
        WHERE u.is_employee = TRUE
          AND u.branch_id = %s
          AND c.check_yn = 'Y'
          AND s.year  = %s
          AND s.month = %s
          AND DATE_FORMAT(u.join_date, '%%Y%%m') <= %s
          AND (
                DATE_FORMAT(u.out_date, '%%Y%%m') IS NULL
             OR DATE_FORMAT(u.out_date, '%%Y%%m') >= %s
          )
        ORDER BY dept_order, position_order, u.join_date
    """

    with connection.cursor() as cur:
        cur.execute(
            query,
            [
                stand_day,
                branch.id,
                stand_day,
                branch.id,
                branch.id,
                branch.id,
                stand_day[0:4],
                stand_day[4:6],
                stand_day[0:6],
                stand_day[0:6],
            ],
        )
        rows = dictfetchall(cur)

    # 템플릿에서 쓰기 좋게 살짝 정리
    return [
        {
            "id": row["user_id"],
            "emp_name": row["emp_name"],
            "dept": row["dept"],
            "position": row["position"],
        }
        for row in rows
    ]
