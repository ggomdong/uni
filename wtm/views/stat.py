import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, PatternFill, Font
from urllib.parse import quote

from datetime import datetime, date
from calendar import monthrange

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models.functions import ExtractDay
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from common.models import Holiday
from common import context_processors
from wtm.services.attendance import build_monthly_metric_details_for_users
from .helpers import sec_to_hhmmss, build_work_status_rows, fetch_base_users_for_month


# 근태기록-월간집계(전체)
@login_required(login_url="common:login")
def work_status(request, stand_ym: str | None = None):
    stand_ym, rows = build_work_status_rows(stand_ym)

    return render(request, "wtm/work_status.html", {
        "stand_ym": stand_ym,
        "rows": rows,
        "active_metric": "all",
    })


# 근태기록-월간집계(전체) 엑셀 다운로드
@login_required(login_url="common:login")
def work_status_excel(request, stand_ym: str | None = None):

    # 공통 빌더로 데이터 얻기
    stand_ym, rows = build_work_status_rows(stand_ym)
    year, month = int(stand_ym[:4]), int(stand_ym[4:6])

    # 정렬 방식 정의
    align_center = Alignment(horizontal="center")
    align_left = Alignment(horizontal="left")
    align_right = Alignment(horizontal="right")

    # 1) 워크북/시트 생성
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "근태기록"

    # 2) 제목 (1행)
    ws["A1"] = f"{year}년 {month}월 근태기록 월간집계(전체)"
    ws["A1"].font = Font(size=10, bold=True)

    # 3) 헤더 (2행)
    headers = [
        "부서",
        "직위",
        "성명",
        "오류(일수)",
        "지각(횟수)",
        "지각(시간)",
        "조퇴(횟수)",
        "조퇴(시간)",
        "연장근로(횟수)",
        "연장근로(시간)",
        "휴일근로(횟수)",
        "휴일근로(시간)",
    ]
    ws.append(headers)

    # 4) 데이터 행 (3행부터)
    for r in rows:
        ws.append([
            r["dept"],
            r["position"],
            r["emp_name"],
            r["error_cnt"],
            r["late_cnt"],
            sec_to_hhmmss(r["late_sec"]),
            r["early_cnt"],
            sec_to_hhmmss(r["early_sec"]),
            r["overtime_cnt"],
            sec_to_hhmmss(r["overtime_sec"]),
            r["holiday_cnt"],
            sec_to_hhmmss(r["holiday_sec"]),
        ])

    # ===== 헤더 스타일(색 + 볼드 + 정렬) =====
    header_fill = PatternFill(
        fill_type="solid",
        start_color="FF02B3BB",
        end_color="FF02B3BB",
    )
    header_font = Font(size=10, bold=True, color="FFFFFFFF")  # 흰색 글자
    header_align = Alignment(horizontal="center", vertical="center")

    # 2행이 헤더 행
    ws.row_dimensions[2].height = 20  # 선택 사항: 헤더 행 높이
    for cell in ws[2]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align

    # 본문(3행~끝)
    # 1~3열(부서, 직위, 성명)은 가운데 정렬, 나머지 숫자/시간 열은 오른쪽 정렬
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=1, max_col=12):
        for cell in row:
            cell.font = Font(size=10)
            if cell.column in (1, 2, 3):  # 부서/직위/성명
                cell.alignment = align_center
            else:  # 오류·지각·조퇴·연장·휴일
                cell.alignment = align_right

    # ===== 컬럼 폭 고정 =====
    # A:부서, B:직위, C:성명, D~L: 숫자/시간
    ws.column_dimensions["A"].width = 15  # 부서
    ws.column_dimensions["B"].width = 15  # 직위
    ws.column_dimensions["C"].width = 15  # 성명

    ws.column_dimensions["D"].width = 12  # 오류(일수)
    ws.column_dimensions["E"].width = 12  # 지각(횟수)
    ws.column_dimensions["F"].width = 14  # 지각(시간)
    ws.column_dimensions["G"].width = 12  # 조퇴(횟수)
    ws.column_dimensions["H"].width = 14  # 조퇴(시간)
    ws.column_dimensions["I"].width = 14  # 연장근로(횟수)
    ws.column_dimensions["J"].width = 14  # 연장근로(시간)
    ws.column_dimensions["K"].width = 14  # 휴일근로(횟수)
    ws.column_dimensions["L"].width = 14  # 휴일근로(시간)

    # 6) HTTP 응답으로 xlsx 전송
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    # 한글처리를 위해 quote()로 감싸기
    filename = quote(f"근태기록-월간집계(전체)_{stand_ym}.xlsx")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response


# 근태기록-월간집계(지각/조퇴/연장/휴일근로)
@login_required(login_url="common:login")
def work_metric(request, metric: str, stand_ym: str | None = None):
    """
    지각/조퇴/연장/휴근 탭 화면 (월간 일자 그리드).
    - unit: month
    - calc: seconds (템플릿에서 HH:MM:SS 포맷)
    """
    _ALLOWED_METRICS = {"late": "지각", "early": "조퇴", "overtime": "연장근로", "holiday": "휴일근로"}
    metric = metric.lower()
    if metric not in _ALLOWED_METRICS:
        return render(request, "wtm/work_metric.html", {
            "error": "잘못된 지표 요청입니다.",
        })

    stand_ym = stand_ym or timezone.now().strftime("%Y%m")
    year, month = int(stand_ym[:4]), int(stand_ym[4:6])

    # 1) 대상자 공통 헬퍼
    base_users = fetch_base_users_for_month(stand_ym)

    if not base_users:
        return render(request, "wtm/work_metric.html", {
            "metric": metric,
            "metric_label": _ALLOWED_METRICS[metric],
            "stand_ym": stand_ym,
            "rows": [],
            "day_list": {}, "holiday_list": [],
            "active_metric": "all",
        })

    # 2) 일자 리스트 (헤더용)
    day_list = context_processors.get_day_list(stand_ym)
    holiday_list = list(
        Holiday.objects
        .filter(holiday__year=stand_ym[0:4], holiday__month=stand_ym[4:6])
        .annotate(day=ExtractDay('holiday'))
        .values_list('day', flat=True)
    )

    # 3) 메트릭 디테일 계산
    uid_list = [u["user_id"] for u in base_users]
    detail_map = build_monthly_metric_details_for_users(users=uid_list, year=year, month=month, metric=metric)

    # 4) 템플릿 rows 구성 (좌측: 부서/직급/성명/횟수/합계, 오른쪽: 일자별 초)
    days_order = list(range(1, monthrange(year, month)[1] + 1))
    rows = []
    for u in base_users:
        d = detail_map.get(u["user_id"], {"days": {}, "count": 0, "total_seconds": 0})
        cell_seconds = [d["days"].get(date(year, month, dd), 0) for dd in days_order]
        rows.append({
            "dept": u["dept"], "position": u["position"], "emp_name": u["emp_name"],
            "count": d["count"], "total_seconds": d["total_seconds"], "cells": cell_seconds,
        })

    return render(request, "wtm/work_metric.html", {
        "metric": metric,
        "metric_label": _ALLOWED_METRICS[metric],
        "stand_ym": stand_ym,
        "day_list": day_list,
        "holiday_list": holiday_list,
        "rows": rows,
        "active_metric": metric,
    })


# 식대
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
        WHERE is_employee = TRUE
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
                    (SELECT d{md[2:4].lstrip("0")}_id
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

    context = {'stand_year': stand_year, 'md_list': md_list, 'user_list': user_list}
    return render(request, 'wtm/work_meal.html', context)