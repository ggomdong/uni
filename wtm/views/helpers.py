from django.utils import timezone
from django.db import connection

from calendar import monthrange

from wtm.services.attendance import build_monthly_attendance_summary_for_users


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


def fetch_base_users_for_month(stand_ym: str) -> list[dict]:
    """
    근태현황/지표 화면 공통: 월 단위 대상 직원 리스트 조회
    - 계약(check_yn='Y') 있는 사람만
    - 스케줄 존재하는 사람만
    - 부서/직위 order + 입사일 순으로 정렬
    """
    year, month = int(stand_ym[:4]), int(stand_ym[4:6])
    first_day = f"{year:04d}{month:02d}01"
    last_day  = f"{year:04d}{month:02d}{monthrange(year, month)[1]:02d}"

    sql = """
        SELECT u.id, u.dept, u.position, u.emp_name
          FROM common_user u
          LEFT JOIN wtm_schedule s ON s.user_id = u.id
         WHERE u.is_employee = TRUE
           AND s.year  = %s
           AND s.month = %s
           AND DATE_FORMAT(u.join_date, '%%Y%%m%%d') <= %s
           AND (DATE_FORMAT(u.out_date, '%%Y%%m%%d') IS NULL OR DATE_FORMAT(u.out_date, '%%Y%%m%%d') >= %s)
           AND EXISTS (
                 SELECT 1
                   FROM wtm_contract c
                  WHERE c.user_id = u.id
                    AND c.check_yn = 'Y'
                    AND (c.user_id, c.stand_date) IN (
                        SELECT a.user_id, MIN(a.stand_date)
                          FROM (
                                SELECT user_id, MAX(stand_date) stand_date FROM wtm_contract WHERE stand_date <= %s GROUP BY user_id
                                UNION
                                SELECT user_id, MIN(stand_date) stand_date FROM wtm_contract WHERE stand_date > %s GROUP BY user_id
                               ) a
                        GROUP BY a.user_id
                    )
               )
        GROUP BY u.id, u.dept, u.position, u.emp_name
        ORDER BY (SELECT `order` FROM common_dept     d WHERE d.dept_name     = u.dept),
                 (SELECT `order` FROM common_position p WHERE p.position_name = u.position),
                 u.join_date
    """
    with connection.cursor() as cur:
        cur.execute(
            sql,
            [
                str(year),
                f"{month:02d}",
                last_day,   # join_date <= last_day
                first_day,  # out_date >= first_day
                last_day,   # contract stand_date <= last_day
                last_day,   # contract stand_date >  last_day
            ],
        )
        return [
            {
                "user_id":  r[0],
                "dept":     r[1] or "",
                "position": r[2] or "",
                "emp_name": r[3] or "",
            }
            for r in cur.fetchall()
        ]


def build_work_status_rows(stand_ym: str | None):
    """
    근태현황(월 요약)에서 사용하는 rows 공통 빌더.
    - stand_ym: 'YYYYMM' 형식 또는 None
    - return: (정규화된 stand_ym, rows 리스트)
    """
    stand_ym = stand_ym or timezone.now().strftime("%Y%m")
    year, month = int(stand_ym[:4]), int(stand_ym[4:6])

    # 1) 대상자 추출
    base_users = fetch_base_users_for_month(stand_ym)

    if not base_users:
        return stand_ym, []

    # 2) 월 요약 계산(초 단위)
    uid_list = [u["user_id"] for u in base_users]
    summary_map = build_monthly_attendance_summary_for_users(
        users=uid_list,
        year=year,
        month=month,
    )

    # 3) rows 구성
    rows = []
    for u in base_users:
        s = summary_map.get(u["user_id"], {})
        rows.append({
            "dept":         u["dept"],
            "position":     u["position"],
            "emp_name":     u["emp_name"],
            "error_cnt":    s.get("error_count", 0),
            "late_cnt":     s.get("late_count", 0),
            "late_sec":     s.get("late_seconds", 0),
            "early_cnt":    s.get("early_count", 0),
            "early_sec":    s.get("early_seconds", 0),
            "overtime_cnt": s.get("overtime_count", 0),
            "overtime_sec": s.get("overtime_seconds", 0),
            "holiday_cnt":  s.get("holiday_count", 0),
            "holiday_sec":  s.get("holiday_seconds", 0),
        })

    return stand_ym, rows


def fetch_log_users_for_day(stand_day: str):
    """
    근무로그 화면에서 사용할 '대상 직원 목록'을 RAW SQL로 조회.
    - contract.check_yn = 'Y'
    - 해당 연월에 스케줄 존재 + 그 날(dN)에 모듈 지정(s.dN_id IS NOT NULL)
    - 재직자(입사/퇴사일 기준)
    - 부서/직위 order 순으로 정렬
    """
    # stand_day: 'YYYYMMDD'
    day_no = int(stand_day[6:8])  # 1~31 → s.d{day_no}_id

    query = f"""
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
            LEFT OUTER JOIN (
                SELECT *
                  FROM wtm_contract
                 WHERE (user_id, stand_date) IN
                 (
                    SELECT a.user_id, MIN(a.stand_date)
                      FROM (
                            SELECT user_id, MAX(stand_date) AS stand_date
                              FROM wtm_contract
                             WHERE stand_date <= '{stand_day}'
                             GROUP BY user_id
                            UNION
                            SELECT user_id, MIN(stand_date) AS stand_date
                              FROM wtm_contract
                             WHERE stand_date > '{stand_day}'
                             GROUP BY user_id
                           ) a
                     GROUP BY a.user_id
                 )
            ) c
                ON u.id = c.user_id
            LEFT OUTER JOIN common_dept d
                ON u.dept = d.dept_name
            LEFT OUTER JOIN common_position p
                ON u.position = p.position_name
        WHERE u.is_employee = TRUE
          AND c.check_yn = 'Y'
          AND s.year  = '{stand_day[0:4]}'
          AND s.month = '{stand_day[4:6]}'
          AND DATE_FORMAT(u.join_date, '%%Y%%m%%d') <= '{stand_day}'
          AND (
                DATE_FORMAT(u.out_date, '%%Y%%m%%d') IS NULL
             OR DATE_FORMAT(u.out_date, '%%Y%%m%%d') >= '{stand_day}'
          )
          AND s.d{day_no}_id IS NOT NULL
        ORDER BY dept_order, position_order, u.join_date
    """

    with connection.cursor() as cur:
        cur.execute(query)
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