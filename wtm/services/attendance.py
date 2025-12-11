from datetime import date, datetime
from calendar import monthrange
from typing import Optional

from django.utils import timezone
from wtm.models import Work, Schedule, Module
from wtm.attendance_calc import (
    LogsDay, to_dt, compute_seconds_status_for_day
)
from types import SimpleNamespace


# 퇴근시간 결정 헬퍼 함수
def determine_checkout_time(
    checkout_dt: Optional[datetime],
    record_day: date,
    checkin_dt: Optional[datetime],
    sched_end_dt: Optional[datetime],
    today: date,
) -> Optional[str]:
    """
    퇴근 시각 결정 로직 통합
    - 실제 퇴근 기록(checkout_dt)이 있으면 그대로 사용
    - 없으면:
      - '어제까지'인 날(record_day < today)이고
      - 출근이 있고(checkin_dt)
      - 출근이 스케줄 종료 이전 또는 같을 때(checkin_dt <= sched_end_dt)
        → 스케줄 종료 시각으로 보정
    """
    # 1) 실제 퇴근 로그가 있으면 사용
    if checkout_dt:
        return checkout_dt.strftime("%H:%M:%S")

    # 2) 퇴근 로그 없을 때: 어제까지 & 출근 ≤ 스케줄 종료 → 스케줄 종료로 보정
    if (
        record_day < today
        and sched_end_dt is not None
        and checkin_dt is not None
        and checkin_dt <= sched_end_dt
    ):
        # 스케줄은 분 단위만 사용하지만, 나중을 위해 초까지 그대로 사용
        return sched_end_dt.strftime("%H:%M:%S")

    return None


# 앱 캘린더에서 사용. 1인 * 1개월
def build_monthly_attendance_for_user(user, year: int, month: int) -> list[dict]:
    """한 사용자에 대한 '월간 일자별 근태' 리스트를 생성."""
    # 1. 스케줄 조회 : Schedule 가져올 때 한 방에 join → 이후 schedule.d1… 접근 시 추가 쿼리 없음
    try:
        schedule = (
            Schedule.objects
            .select_related(*[f'd{i}' for i in range(1, 32)])
            .get(user=user, year=str(year), month=f"{month:02d}")
        )
    except Schedule.DoesNotExist:
        return []

    # 2. 근태 기록 조회
    works = (
        Work.objects
        .filter(user=user, record_day__year=year, record_day__month=month)
        .values('record_day', 'work_code', 'record_date')
        .order_by('record_day', 'record_date')
    )

    # 날짜별로 출퇴근 매핑
    work_map: dict[date, dict[str, list[datetime]]] = {}
    for w in works:
        day = w["record_day"]
        code = w["work_code"]  # "I" 또는 "O"
        if day not in work_map:
            work_map[day] = {"I": [], "O": []}
        work_map[day][code].append(w["record_date"])

    # 3. 월간 루프 돌면서 데이터 구성
    results: list[dict] = []
    days_in_month = monthrange(year, month)[1]
    today = timezone.now().date()

    for day in range(1, days_in_month + 1):
        record_day = date(year, month, day)
        module: Module = getattr(schedule, f"d{day}", None)

        # 출퇴근 기록 목록 (이미 record_date 기준 정렬됨)
        ins = work_map.get(record_day, {}).get("I", [])
        outs = work_map.get(record_day, {}).get("O", [])

        # 출근 시각 (가장 이른 I)
        checkin_dt = ins[0] if ins else None
        checkin_time = checkin_dt.strftime("%H:%M:%S") if checkin_dt else None

        # 스케줄 종료시각 파싱
        sched_end_hhmm = module.end_time if (module and module.end_time and module.end_time != "-") else None
        sched_end_dt = to_dt(record_day, sched_end_hhmm) if sched_end_hhmm else None

        # 퇴근 datetime (가장 늦은 O)
        checkout_dt = outs[-1] if outs else None

        # 퇴근 시각 결정 (공통 헬퍼 사용)
        checkout_time = determine_checkout_time(
            checkout_dt=checkout_dt,
            record_day=record_day,
            checkin_dt=checkin_dt,
            sched_end_dt=sched_end_dt,
            today=today,
        )

        # 최종 로그 (보정 결과 포함)
        log = LogsDay(
            checkin=checkin_time,
            checkout=checkout_time,
        )

        # compute_seconds_status_for_day 로 초 단위 계산
        res = compute_seconds_status_for_day(record_day, module, log)

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

            # 초 단위 지표(휴게 반영)
            "late_seconds": res.late_seconds,
            "early_seconds": res.early_seconds,
            "overtime_seconds": res.overtime_seconds,
            "holiday_seconds": res.holiday_seconds,

            # 프런트 편의
            "is_late": res.late_seconds > 0,
            "is_early_checkout": res.early_seconds > 0,
            "is_overtime": res.overtime_seconds > 0,
        })

    return results


# 웹 초기화면 근무현황에서 활용. 전체 사용자 * 1일
def build_daily_attendance_for_users(base_rows: list[dict], day: date) -> list[dict]:
    """
    인덱스 화면 하단 '근무현황' 표용 work_list를 생성한다.
    - base_rows: 뷰에서 실행한 기존 SQL 결과(dict 리스트). (dept, position, emp_name, start_time, end_time, cat 등 포함)
    - day: 기준 일자 (datetime.date)
    정책:
      - 체크아웃 보정: 오늘은 보정 안 함. 과거일이고 (출근 ≤ 스케줄 종료)일 때만 스케줄 종료로 보정.
      - 초/상태 계산은 compute_seconds_status_for_day 재사용.
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

        checkin_dt = first_in.get(uid)
        checkin_time = checkin_dt.strftime("%H:%M:%S") if checkin_dt else None

        sched_end_hhmm = r["end_time"] if r.get("end_time") and r["end_time"] != "-" else None
        sched_end_dt = to_dt(day, sched_end_hhmm) if sched_end_hhmm else None

        checkout_dt = last_out.get(uid)

        checkout_time = determine_checkout_time(
            checkout_dt=checkout_dt,
            record_day=day,
            checkin_dt=checkin_dt,
            sched_end_dt=sched_end_dt,
            today=today,
        )

        metrics = compute_seconds_status_for_day(
            record_day=day,
            module=mod,
            log=LogsDay(checkin=checkin_time, checkout=checkout_time),
        )

        work_list.append({
            "user_id": uid,
            "dept": r["dept"],
            "position": r["position"],
            "emp_name": r["emp_name"],
            "cat": r.get("cat"),
            "module_id": r.get("module_id"),
            "start_time": r.get("start_time"),
            "end_time": r.get("end_time"),
            "checkin_time": checkin_time,
            "checkout_time": checkout_time,
            "late_seconds": metrics.late_seconds,
            "early_seconds": metrics.early_seconds,
            "overtime_seconds": metrics.overtime_seconds,
            "holiday_seconds": metrics.holiday_seconds,
            "status": metrics.status,
            "status_codes": metrics.status_codes,
            "status_labels": metrics.status_labels,
        })

    return work_list


def prepare_month(users: list[int], year: int, month: int):
    """
    (단일 함수) 월 화면 공통 준비:
      - days: 월의 모든 일자 리스트
      - sched_map: {user_id: {date: module_id|None}}
      - modules: {module_id: Module}
      - logs_map: {user_id: {date: {"I":[dt...], "O":[dt...]}}}
    ORM 왕복: Schedule(1) + Module in_bulk(1) + Work(1)
    """
    # 1) 월 일자
    last = monthrange(year, month)[1]
    days = [date(year, month, d) for d in range(1, last + 1)]

    # 2) 스케줄 bulk (d1_id ~ dN_id)
    cols = [f"d{d}_id" for d in range(1, last + 1)]
    sched_rows = (
        Schedule.objects
        .filter(user_id__in=users, year=f"{year:04d}", month=f"{month:02d}")
        .values("user_id", *cols)
    )
    sched_map: dict[int, dict[date, int | None]] = {uid: {} for uid in users}
    module_ids: set[int] = set()
    for r in sched_rows:
        uid = int(r["user_id"])
        for i, rd in enumerate(days, start=1):
            mid = r.get(f"d{i}_id")
            sched_map[uid][rd] = mid
            if mid:
                module_ids.add(mid)

    # 3) 모듈 캐시
    modules: dict[int, Module] = Module.objects.in_bulk(module_ids) if module_ids else {}

    # 4) 로그 bulk
    works = (
        Work.objects
        .filter(user_id__in=users, record_day__year=year, record_day__month=month)
        .values("user_id", "record_day", "work_code", "record_date")
        .order_by("user_id", "record_day", "record_date")
    )

    logs_map: dict[int, dict[date, dict[str, list]]] = {}
    for w in works:
        uid = int(w["user_id"])
        rd = w["record_day"]
        code_raw = (w["work_code"] or "").upper()
        code = "I" if code_raw == "I" else ("O" if code_raw == "O" else None)
        if code is None:
            continue  # 방어: I/O 외의 값이 있으면 무시

        user_map = logs_map.setdefault(uid, {})
        day_map = user_map.setdefault(rd, {"I": [], "O": []})
        day_map.setdefault(code, []).append(w["record_date"])

    return days, sched_map, modules, logs_map


def build_monthly_attendance_summary_for_users(*, users: list[int], year: int, month: int) -> dict[int, dict]:
    """
    [웹 근태현황 요약표] 전체 사용자 × 1개월, 초(second) 단위 합계/횟수.
    반환: {
      user_id: {
        late_count,     late_seconds,
        early_count,    early_seconds,
        overtime_count, overtime_seconds,
        holiday_count,  holiday_seconds,
        error_count,
      }, ...
    }
    """
    if not users:
        return {}

    today = timezone.now().date()

    days, sched_map, modules, logs_map = prepare_month(users, year, month)

    summary: dict[int, dict] = {}
    for uid in users:
        agg = {
            "late_count": 0, "late_seconds": 0,
            "early_count": 0, "early_seconds": 0,
            "overtime_count": 0, "overtime_seconds": 0,
            "holiday_count": 0, "holiday_seconds": 0,
            "error_count": 0,
        }
        for rd in days:
            mid = sched_map.get(uid, {}).get(rd)
            module = modules.get(mid) if mid else None

            ins  = logs_map.get(uid, {}).get(rd, {}).get("I", [])
            outs = logs_map.get(uid, {}).get(rd, {}).get("O", [])

            # --- 출근 dt / 시간 ---
            checkin_dt = min(ins) if ins else None
            checkin_time = checkin_dt.strftime("%H:%M:%S") if checkin_dt else None

            # --- 스케줄 종료 dt ---
            sched_end_hhmm = None
            if module and getattr(module, "end_time", None) and module.end_time != "-":
                sched_end_hhmm = module.end_time
            sched_end_dt = to_dt(rd, sched_end_hhmm) if sched_end_hhmm else None

            # --- 실제 퇴근 로그 dt ---
            checkout_dt = max(outs) if outs else None

            # --- 공통 퇴근 보정 정책 적용 ---
            checkout_time = determine_checkout_time(
                checkout_dt=checkout_dt,
                record_day=rd,
                checkin_dt=checkin_dt,
                sched_end_dt=sched_end_dt,
                today=today,
            )

            # --- 코어 계산 ---
            m = compute_seconds_status_for_day(
                record_day=rd,
                module=module,
                log=LogsDay(checkin=checkin_time, checkout=checkout_time),
            )

            if m.late_seconds     > 0: agg["late_count"]     += 1
            if m.early_seconds    > 0: agg["early_count"]    += 1
            if m.overtime_seconds > 0: agg["overtime_count"] += 1
            if m.holiday_seconds  > 0: agg["holiday_count"]  += 1
            if m.status_codes == ["ERROR"]:
                agg["error_count"] += 1

            agg["late_seconds"]     += m.late_seconds
            agg["early_seconds"]    += m.early_seconds
            agg["overtime_seconds"] += m.overtime_seconds
            agg["holiday_seconds"]  += m.holiday_seconds

        summary[uid] = agg

    return summary


def build_monthly_metric_details_for_users(
    *, users: list[int], year: int, month: int, metric: str
) -> dict[int, dict]:
    """
    지각(late) / 조퇴(early) / 연장(overtime) / 휴근(holiday) 중 하나의 메트릭에 대해
    전체 사용자 × 1개월의 '일자별 초'와 '합계/횟수'를 반환.

    반환:
    {
      user_id: {
        "days": { date: seconds(int) },  # 월의 모든 날짜 키 포함(없으면 0)
        "count": int,                     # seconds>0 인 일수
        "total_seconds": int,             # 월 누적 초
      },
      ...
    }
    """
    key = {
        "late": "late_seconds",
        "early": "early_seconds",
        "overtime": "overtime_seconds",
        "holiday": "holiday_seconds",
    }.get(metric)
    if not key:
        raise ValueError("metric must be one of: late, early, overtime, holiday")
    if not users:
        return {}

    today = timezone.now().date()

    days, sched_map, modules, logs_map = prepare_month(users, year, month)

    result: dict[int, dict] = {}
    for uid in users:
        day_map: dict[date, int] = {d: 0 for d in days}
        cnt = 0
        total = 0

        for rd in days:
            mid = sched_map.get(uid, {}).get(rd)
            module = modules.get(mid) if mid else None

            user_map = logs_map.get(uid, {})
            day_log = user_map.get(rd, {"I": [], "O": []})
            ins = day_log.get("I", [])
            outs = day_log.get("O", [])

            # --- 출근 dt / 시간 ---
            checkin_dt = min(ins) if ins else None
            checkin_time = checkin_dt.strftime("%H:%M:%S") if checkin_dt else None

            # --- 스케줄 종료 dt ---
            sched_end_hhmm = None
            if module and getattr(module, "end_time", None) and module.end_time != "-":
                sched_end_hhmm = module.end_time
            sched_end_dt = to_dt(rd, sched_end_hhmm) if sched_end_hhmm else None

            # --- 실제 퇴근 로그 dt ---
            checkout_dt = max(outs) if outs else None

            # --- 공통 퇴근 보정 정책 적용 ---
            checkout_time = determine_checkout_time(
                checkout_dt=checkout_dt,
                record_day=rd,
                checkin_dt=checkin_dt,
                sched_end_dt=sched_end_dt,
                today=today,
            )

            # --- 코어 계산 ---
            m = compute_seconds_status_for_day(
                record_day=rd,
                module=module,
                log=LogsDay(checkin=checkin_time, checkout=checkout_time),
            )
            seconds = getattr(m, key)
            day_map[rd] = seconds
            if seconds > 0:
                cnt += 1
                total += seconds

        result[uid] = {"days": day_map, "count": cnt, "total_seconds": total}
    return result