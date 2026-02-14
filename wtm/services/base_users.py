from calendar import monthrange

from django.db import connection


def fetch_base_users_for_month(stand_ym: str, *, branch, is_contract_checked: bool = True) -> list[dict]:
    """
    월 단위 대상 직원 리스트 조회
    - 근태확인(check_yn='Y') 여부는 is_contract_checked
    - 근무표 존재하는 사람만
    - 부서/직위 order + 입사일, 이름 순으로 정렬
    """
    year, month = int(stand_ym[:4]), int(stand_ym[4:6])
    first_day = f"{year:04d}{month:02d}01"
    last_day = f"{year:04d}{month:02d}{monthrange(year, month)[1]:02d}"

    contract_sql = ""
    contract_params = []

    if is_contract_checked:
        contract_sql = """
               AND EXISTS (
                     SELECT 1
                       FROM wtm_contract c
                      WHERE c.user_id = u.id
                        AND c.check_yn = 'Y'
                        AND c.branch_id = %s
                        AND (c.user_id, c.stand_date) IN (
                            SELECT a.user_id, MIN(a.stand_date)
                              FROM (
                                    SELECT user_id, MAX(stand_date) stand_date FROM wtm_contract WHERE stand_date <= %s AND branch_id = %s GROUP BY user_id
                                    UNION
                                    SELECT user_id, MIN(stand_date) stand_date FROM wtm_contract WHERE stand_date > %s AND branch_id = %s GROUP BY user_id
                                   ) a
                            GROUP BY a.user_id
                        )
                   )
            """
        contract_params = [branch.id, last_day, branch.id, last_day, branch.id]

    sql = f"""
            SELECT u.id, u.dept, u.position, u.emp_name, DATE_FORMAT(u.out_date, '%%Y%%m%%d') AS out_ymd
              FROM common_user u
              INNER JOIN wtm_schedule s ON s.user_id = u.id
             WHERE u.is_employee = TRUE
               AND u.is_active = TRUE
               AND u.branch_id = %s
               AND s.branch_id = u.branch_id
               AND s.year  = %s
               AND s.month = %s
               AND DATE_FORMAT(u.join_date, '%%Y%%m%%d') <= %s
               AND (DATE_FORMAT(u.out_date, '%%Y%%m%%d') IS NULL OR DATE_FORMAT(u.out_date, '%%Y%%m%%d') >= %s)
               {contract_sql}
            GROUP BY u.id, u.dept, u.position, u.emp_name
            ORDER BY (SELECT `order` FROM common_dept     d WHERE d.dept_name     = u.dept AND d.branch_id = u.branch_id),
                     (SELECT `order` FROM common_position p WHERE p.position_name = u.position AND p.branch_id = u.branch_id),
                     u.join_date,
                     u.emp_name
        """

    params = [
        branch.id,
        str(year),
        f"{month:02d}",
        last_day,
        first_day,
        *contract_params,
    ]

    with connection.cursor() as cur:
        cur.execute(sql, params)
        return [
            {
                "user_id": r[0],
                "dept": r[1] or "",
                "position": r[2] or "",
                "emp_name": r[3] or "",
                "out_ymd": r[4] or None,
            }
            for r in cur.fetchall()
        ]
