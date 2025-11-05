# wtm/services/attendance_builder.py
# from __future__ import annotations
from datetime import date
from calendar import monthrange
from django.utils import timezone
from wtm.models import Work, Schedule, Module
from wtm.attendance_calc import (
    LogsDay, to_dt, compute_minutes_status_for_day
)
from types import SimpleNamespace

# 앱 캘린더에서 사용. 1인 * 1개월
def build_monthly_attendance_for_user(user, year: int, month: int) -> list[dict]:
    """한 사용자에 대한 '월간 일자별 근태' 리스트를 생성."""
    # 1. 스케줄 조회
    try:
        schedule = Schedule.objects.get(
            user=user, year=str(year), month=f"{month:02d}"
        )
    except Schedule.DoesNotExist:
        return []

    # 2. 근태 기록 조회
    works = Work.objects.filter(user=user, record_day__year=year, record_day__month=month)

    # 날짜별로 출퇴근 매핑
    work_map = {}
    for w in works:
        day = w.record_day
        if day not in work_map:
            work_map[day] = {"I": [], "O": []}
        work_map[day][w.work_code].append(w)

    # 3. 월간 루프 돌면서 데이터 구성
    results: list[dict] = []
    days_in_month = monthrange(year, month)[1]
    today = timezone.now().date()

    for day in range(1, days_in_month + 1):
        record_day = date(year, month, day)
        module: Module = getattr(schedule, f"d{day}", None)

        work_in_list = work_map.get(record_day, {}).get("I", [])
        work_out_list = work_map.get(record_day, {}).get("O", [])

        work_in = min(work_in_list, key=lambda w: w.record_date) if work_in_list else None
        work_out = max(work_out_list, key=lambda w: w.record_date) if work_out_list else None

        # 화면용 HH:mm 문자열
        checkin_time = work_in.record_date.strftime("%H:%M") if work_in else None

        # 스케줄 종료시각 파싱
        sched_end_hhmm = module.end_time if (module and module.end_time and module.end_time != "-") else None
        sched_end_dt = to_dt(record_day, sched_end_hhmm) if sched_end_hhmm else None  # 스케줄 종료 datetime

        # 출근 datetime
        checkin_dt = to_dt(record_day, checkin_time) if checkin_time else None  # "HH:mm" → dt

        # 퇴근시각 결정 (정책)
        # 1) 실제 퇴근 로그가 있으면 그대로 사용
        # 2) 없으면 '어제까지'이고 '출근 ≤ 스케줄 종료'일 때만 스케줄 종료로 보정
        if work_out:
            checkout_time = work_out.record_date.strftime("%H:%M")
        else:
            if (record_day < today) and sched_end_dt and checkin_dt and (checkin_dt <= sched_end_dt):
                checkout_time = sched_end_hhmm
            else:
                checkout_time = None

        # 최종 로그 (보정 결과 포함)
        log = LogsDay(
            checkin=checkin_time,
            checkout=checkout_time,
        )

        # compute_minutes_for_day 로 분 계산
        res = compute_minutes_status_for_day(record_day, module, log)

        results.append({
            "record_day": record_day,
            "work_start": module.start_time if module else None,
            "work_end": module.end_time if module else None,
            "checkin_time": checkin_time,
            "checkout_time": checkout_time,

            # 상태(앱은 status_codes/labels 배열을 쓰면 됨)
            "status": res.status,
            "status_codes": res.status_codes,  # ["REGULAR","LATE",...]
            "status_labels": res.status_labels,  # ["정규근무","지각",...]

            # 모듈
            "work_cat": module.cat if module else None,
            "work_name": module.name if module else None,

            # 분 단위 지표(휴게 반영)
            "late_minutes": res.late_minutes,
            "early_minutes": res.early_minutes,
            "overtime_minutes": res.overtime_minutes,
            "holiday_minutes": res.holiday_minutes,

            # 프런트 편의
            "is_late": res.late_minutes > 0,
            "is_early_checkout": res.early_minutes > 0,
            "is_overtime": res.overtime_minutes > 0,
        })

    return results


# 웹 초기화면 근무현황에서 활용. 전체 사용자 * 1일
def build_work_list_for_index(base_rows: list[dict], day: date) -> list[dict]:
    """
    인덱스 화면 하단 '근무현황' 표용 work_list를 생성한다.
    - base_rows: 뷰에서 실행한 기존 SQL 결과(dict 리스트). (dept, position, emp_name, start_time, end_time, cat 등 포함)
    - day: 기준 일자 (datetime.date)
    정책:
      - 체크아웃 보정: 오늘은 보정 안 함. 과거일이고 (출근 ≤ 스케줄 종료)일 때만 스케줄 종료로 보정.
      - 분/상태 계산은 compute_minutes_status_for_day 재사용.
    반환:
      - 템플릿(index.html)의 컬럼명에 맞춘 dict 리스트.
    """
    if not base_rows:
        return []

    today = timezone.now().date()

    # 1) 사용자 id 수집 (순서 보존)
    user_ids = []
    seen = set()
    for r in base_rows:
        uid = r.get("user_id")
        if uid and uid not in seen:
            user_ids.append(uid)
            seen.add(uid)

    # 2) 해당 일자 로그 일괄 조회 → 최초 IN / 최종 OUT
    works = (
        Work.objects
        .filter(user_id__in=user_ids, record_day=day)
        .only("user_id", "work_code", "record_date")
        .order_by("record_date")
    )
    first_in: dict[int, "datetime"] = {}
    last_out: dict[int, "datetime"] = {}
    for w in works:
        if w.work_code == "I":
            first_in.setdefault(w.user_id, w.record_date)
        elif w.work_code == "O":
            prev = last_out.get(w.user_id)
            if prev is None or w.record_date > prev:
                last_out[w.user_id] = w.record_date

    # 3) 공통 코어 호출하여 분/상태 계산
    work_list: list[dict] = []
    for r in base_rows:
        uid = r["user_id"]

        # 모듈 래핑(코어가 기대하는 속성만 제공)
        mod = None
        if r.get("start_time") and r.get("end_time") and r.get("cat"):
            mod = SimpleNamespace(
                cat=r["cat"],
                name=r.get("name"),
                start_time=r["start_time"],
                end_time=r["end_time"],
                rest1_start_time=r.get("rest1_start_time"),
                rest1_end_time=r.get("rest1_end_time"),
                rest2_start_time=r.get("rest2_start_time"),
                rest2_end_time=r.get("rest2_end_time"),
            )

        # IN/OUT HH:mm
        checkin_time = first_in[uid].strftime("%H:%M") if uid in first_in else None

        # 스케줄 종료
        sched_end_hhmm = r["end_time"] if r.get("end_time") and r["end_time"] != "-" else None
        sched_end_dt = to_dt(day, sched_end_hhmm) if sched_end_hhmm else None
        checkin_dt = to_dt(day, checkin_time) if checkin_time else None

        # 체크아웃 결정 (보정 정책)
        if uid in last_out:
            checkout_time = last_out[uid].strftime("%H:%M")
        else:
            if (day < today) and sched_end_dt and checkin_dt and (checkin_dt <= sched_end_dt):
                checkout_time = sched_end_hhmm
            else:
                checkout_time = None

        metrics = compute_minutes_status_for_day(
            record_day=day,
            module=mod,
            log=LogsDay(checkin=checkin_time, checkout=checkout_time),
        )

        work_list.append({
            "dept": r["dept"],
            "position": r["position"],
            "emp_name": r["emp_name"],
            "cat": r.get("cat"),
            "start_time": r.get("start_time"),
            "end_time": r.get("end_time"),
            "checkin_time": checkin_time,
            "checkout_time": checkout_time,
            "late_minutes": metrics.late_minutes,
            "early_minutes": metrics.early_minutes,
            "overtime_minutes": metrics.overtime_minutes,
            "holiday_minutes": metrics.holiday_minutes,
            # 필요 시:
            "status": metrics.status,
            "status_codes": metrics.status_codes,
            "status_labels": metrics.status_labels,
        })

    return work_list