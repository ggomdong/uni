# -----------------------------------------------------------------------------
# 근로/휴게/지각/조퇴/연장 계산의 "핵심 공통 로직".
# - 근로모듈의 "유급 근로 시간대"를 구간(segments)으로 만들고,
# - 실제 체류(출근~퇴근)와의 '구간 연산'으로 각 지표(지각/조퇴/연장/휴일근로)를 계산한다.
# - 모든 지표는 '초(second)'를 기준으로 산출한다.
#
# ※ 이 모듈은 "순수 함수"들로만 구성되어 있으므로
#    DRF API, Django 템플릿 뷰, 백오피스 커맨드, 배치 등 어디서든 같은 결과를 재사용할 수 있다.
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime, date
from django.utils import timezone
from common.context_processors import STATUS_LABELS
from typing import List, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from wtm.models import Module  # 타입체커 전용, 런타임 미임포트

# 타입 별칭: (start_dt, end_dt) 쌍의 리스트
Segment = Tuple[datetime, datetime]

@dataclass
class LogsDay:
    checkin: Optional[str]             # "HH:mm" (최초)
    checkout: Optional[str]            # "HH:mm" (최종)

@dataclass
class Metrics:
    late_seconds: int
    early_seconds: int
    overtime_seconds: int
    holiday_seconds: int
    status: str
    status_codes: list[str]
    status_labels: list[str]


def to_dt(day: date, hhmmss: Optional[str]) -> Optional[datetime]:
    """
    'HH:mm:ss' 또는 'HH:mm' 문자열을 datetime으로 변환.
    None 또는 "-"는 유효하지 않은 시각으로 간주하여 None 반환.
    """
    if hhmmss is None:
        return None

    time_str = hhmmss.strip()
    if time_str in ("", "-"):
        return None

    try:
        if len(time_str) == 5:  # HH:mm
            time_str += ":00"
        elif len(time_str) != 8:  # HH:mm:ss 아니면 에러 취급
            return None

        time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
        return datetime.combine(day, time_obj)
    except ValueError:
        return None


def make_paid_segments(day: date, module: "Module") -> List[Segment]:
    """
    하나의 모듈(근무표)에서 '유급 근로 세그먼트' 리스트를 생성.
    - 근로 전체 구간: (start_time ~ end_time)
    - 휴게 구간: (rest1_start~rest1_end), (rest2_start~rest2_end) [0~2개]
    - 유급 = 전체 - 휴게 (겹침/순서는 정렬·클리핑으로 정리)
    """
    # 근로 구간 파싱
    if not module or not module.start_time or not module.end_time \
       or module.start_time == "-" or module.end_time == "-":
        return []

    S = to_dt(day, module.start_time)
    E = to_dt(day, module.end_time)
    # 비정상 혹은 0분 근로는 유급세그먼트 없음
    if not S or not E or E <= S:
        return []

    # 휴게 구간 파싱(있으면 추가)
    rests: List[Segment] = []
    r1s, r1e = to_dt(day, getattr(module, "rest1_start_time", None)), to_dt(day, getattr(module, "rest1_end_time", None))
    r2s, r2e = to_dt(day, getattr(module, "rest2_start_time", None)), to_dt(day, getattr(module, "rest2_end_time", None))
    if r1s and r1e and r1e > r1s: rests.append((r1s, r1e))
    if r2s and r2e and r2e > r2s: rests.append((r2s, r2e))

    # 1) 근로 전체에서 시작
    segments: List[Segment] = [(S, E)]

    # 2) 휴게 구간들을 시간순으로 적용하면서, 그 부분을 잘라낸다.
    for rs, re in sorted(rests, key=lambda x: x[0]):
        new_segments: List[Segment] = []
        for a, b in segments:
            # (a,b)와 (rs,re)가 겹치지 않으면 그대로 보존
            if re <= a or b <= rs:
                new_segments.append((a, b))
                continue

            # 겹치는 경우, '좌측 잔여' / '우측 잔여'로 잘라서 추가
            # 예: (09:00~18:00) - (12:00~13:00) => (09:00~12:00), (13:00~18:00)
            if rs > a:
                new_segments.append((a, rs))
            if re < b:
                new_segments.append((re, b))
        segments = new_segments

        # 매 스텝 이후에도 (end > start)만 남도록 자연히 보장됨

    # 3) 혹시 모를 0분/역전구간 제거 (안전망)
    return [(a, b) for (a, b) in segments if b > a]


def seconds_before(t: Optional[datetime], segments: Sequence[Segment]) -> int:
    """
    시각 t '이전'의 유급 근로 누적 초.
    - '지각(late)' 계산에 사용: 근무표 상의 유급 근로가 시작됐는데, 출근(t)이 그 이후라면
      t 이전의 유급 근로가 모두 지각 초로 잡힌다.
    """
    if t is None:
        return 0
    total = 0
    for a, b in segments:
        if t <= a:
            continue
        if t >= b:
            total += int((b - a).total_seconds())
        else:
            total += int((t - a).total_seconds())
            break # 이후 세그먼트는 불필요
    return total


def seconds_after(t: Optional[datetime], segments: Sequence[Segment]) -> int:
    """
    시각 t '이후'의 유급 근로 누적 초.
    - '조퇴(early)' 계산에 사용: 근무표 상의 유급 근로가 남아 있는데, 퇴근(t)이 그 이전이라면
      t 이후의 유급 근로가 모두 조퇴 초로 잡힌다.
    """
    if t is None:
        return 0
    total = 0
    for a, b in segments:
        if t >= b:
            continue
        if t <= a:
            total += int((b-a).total_seconds())
        else:
            total += int((b-t).total_seconds())
    return total


def intersection_seconds(a: Optional[datetime], b: Optional[datetime], segments: Sequence[Segment]) -> int:
    """
    체류 구간 [a, b) 과 유급 세그먼트들의 교집합 총 초.
    사용처:
    - presence_paid_seconds: 실제 유급 체류 여부/양을 판단 (ERROR 판정 등)
    - compute_overtime_seconds: '유급구간에 전혀 머물지 않은 경우 연장 0' 가드
    """
    if a is None or b is None or b <= a:
        return 0
    total = 0
    for s, e in segments:
        # 각 세그먼트와 [a, b) 교집합
        x, y = max(a, s), min(b, e)
        if y > x:
            total += int((y - x).total_seconds())

    return total


def last_paid_end(segments: Sequence[Segment]) -> Optional[datetime]:
    """
    유급 근로 세그먼트들 중 가장 늦은 '끝' 시각.
    - '연장(overtime)' 계산에 사용: 마지막 유급 종료 이후 실제 퇴근까지의 분.
    """
    return max((e for _, e in segments), default=None)


def compute_overtime_seconds(
    checkin: Optional[datetime],
    checkout: Optional[datetime],
    segments: Sequence[Segment],
) -> int:
    """
    연장(overtime) 초 산출.
    - 근무표 유급세그먼트와 실제 근로의 교집합이 0이면 연장 0.
    - 마지막 유급 종료 이후 실제 퇴근까지의 초를 연장으로 인정.
    """
    if not checkin or not checkout:
        return 0
    last_end = last_paid_end(segments)
    if not last_end:
        return 0

    # 핵심 가드: 근무표 유급세그먼트와 실제 근로의 교집합이 0이면 연장 없음
    paid_overlap = intersection_seconds(checkin, min(checkout, last_end), segments)
    if paid_overlap == 0:
        return 0

    # 연장 계산 (유예 분 없음)
    if checkout <= last_end:
        return 0
    return int((checkout - last_end).total_seconds())


def compute_holiday_seconds(
    module: "Module | None",
    has_checkin: bool,
    has_checkout: bool,
    segments: Sequence[Segment],
) -> int:
    """
    휴일근로 초 산출.

    - 모듈이 '휴일근로'일 때만 대상.
    - 출근/퇴근 로그가 모두 있는 날만 계산.
    - 근무표 유급세그먼트(시업~종업 - 휴게)의 전체 길이를
      휴일근로시간으로 본다.
      (지각/조퇴는 별도 지표(late/early)로 분리되어 있으므로
       여기서는 차감하지 않음)
    """
    if not module or module.cat != "휴일근로":
        return 0
    if not has_checkin or not has_checkout:
        return 0

    total = 0
    for a, b in segments:
        total += int((b - a).total_seconds())
    return total


def compute_seconds_status_for_day(record_day: date, module: "Module | None", log: LogsDay) -> Metrics:
    """
    하루(record_day)에 대해 초(second) 지표 + 상태코드를 계산한다.
    - I/O 없음 (순수 함수)
    - 휴게는 유급 세그먼트에서 제외되어 자연스럽게 반영됨
    """
    ######### 공통 ##########

    # 1) 휴게 반영 유급 세그먼트 생성
    paid_segments = make_paid_segments(record_day, module)
    paid_total_seconds = sum(
        int((b - a).total_seconds()) for a, b in paid_segments
    )

    # 2) 출퇴근 dt
    checkin_dt = to_dt(record_day, log.checkin)
    checkout_dt = to_dt(record_day, log.checkout)
    has_checkin = bool(checkin_dt)
    has_checkout = bool(checkout_dt)

    # 실 체류 ∩ 유급
    presence_paid_seconds = intersection_seconds(checkin_dt, checkout_dt, paid_segments) if (
                has_checkin and has_checkout) else 0
    has_paid_presence = (presence_paid_seconds > 0)

    ######### 시간 계산 ##########

    # 1) 지각/조퇴
    late_seconds = seconds_before(checkin_dt, paid_segments)
    early_seconds = seconds_after(checkout_dt, paid_segments)
    # # 유급 구간에 실제로 머문 시간이 '있을 때만' 지각/조퇴를 계산한다.
    # # (유급 교집합 0이면 근무 자체가 없으므로 마이너스 근태를 계산하지 않음)
    # if has_paid_presence:
    #     late_seconds = seconds_before(checkin_dt, paid_segments)
    #     early_seconds = seconds_after(checkout_dt, paid_segments)
    # else:
    #     late_seconds = 0
    #     early_seconds = 0

    # 2) 연장
    overtime_seconds = compute_overtime_seconds(checkin_dt, checkout_dt, paid_segments)
    # 동일한 이유로 유급 교집합 0이면 연장도 0
    # if has_paid_presence:
    #     overtime_seconds = compute_overtime_seconds(checkin_dt, checkout_dt, paid_segments)
    # else:
    #     overtime_seconds = 0

    # 3) 휴일근로: 스케줄 유급시간(시업~종업 - 휴게), 지각/조퇴 미차감
    holiday_seconds = compute_holiday_seconds(
        module=module,
        has_checkin=has_checkin,
        has_checkout=has_checkout,
        segments=paid_segments,
    )

    ######### 상태 정의 ##########

    # 오늘 이후의 상태 판정을 위한 변수 설정
    now = timezone.now()
    today = now.date()
    is_today = (record_day == today)
    is_future = (record_day > today)

    # 0) 근무표 자체가 없으면
    if not module:
        status_codes = ["NOSCHEDULE"]

    else:
        cat = module.cat

        # 날짜(미래/오늘/과거) 무관: '출근시각' 없이 '퇴근시각'만 있으면 무조건 오류
        if has_checkout and not has_checkin:
            status_codes = ["ERROR"]

        else:
            def is_error_on_workday() -> bool:
                """
                오류 판정 로직
                - 오늘: 시업시간 지났는데 출퇴근 기록 전무 OR (체류∩유급 0)
                - 과거: 출퇴근 기록 전무 OR (체류∩유급 0)
                """
                if is_today:
                    sched_start_hhmm = (
                        module.start_time
                        if (module.start_time and module.start_time != "-")
                        else None
                    )
                    sched_start_dt = to_dt(record_day, sched_start_hhmm) if sched_start_hhmm else None

                    start_passed_no_check = (
                            sched_start_dt is not None
                            and now >= sched_start_dt
                            and (not has_checkin and not has_checkout)
                    )

                    wrong_logs = (
                            has_checkin and has_checkout
                            and paid_total_seconds > 0
                            and presence_paid_seconds == 0
                    )
                    return start_passed_no_check or wrong_logs

                # 과거
                return (
                        (not has_checkin and not has_checkout) or
                        (paid_total_seconds > 0 and has_checkin and has_checkout and presence_paid_seconds == 0)
                )

            # =====================================================================
            # 1) 소정근로
            #    - 미래: NORMAL
            #    - 오늘/과거: 오류 먼저, 아니면 LATE/EARLY/OVERTIME 조합, 없으면 NORMAL
            # =====================================================================
            if cat == "소정근로":
                if is_future:
                    status_codes = ["NORMAL"]
                else:
                    if is_error_on_workday():
                        status_codes = ["ERROR"]
                    else:
                        status_codes = []
                        # 지각, 조퇴, 지각+조퇴, 지각+연장 판정
                        if late_seconds > 0:
                            status_codes.append("LATE")
                        if early_seconds > 0:
                            status_codes.append("EARLY")
                        if overtime_seconds > 0:
                            status_codes.append("OVERTIME")

                        if not status_codes:
                            status_codes = ["NORMAL"]

            # =====================================================================
            # 2) 휴일근로
            #    - 미래: HOLIDAY
            #    - 오늘/과거: 오류면 ERROR, 아니면 HOLIDAY 단일
            # =====================================================================
            elif cat == "휴일근로":
                if is_future:
                    status_codes = ["HOLIDAY"]
                else:
                    status_codes = ["ERROR"] if is_error_on_workday() else ["HOLIDAY"]

            # =====================================================================
            # 3) OFF
            #    - 기록 없음: OFF
            #    - 기록 있음: ERROR
            # =====================================================================
            elif cat == "OFF":
                status_codes = ["ERROR"] if (has_checkin or has_checkout) else ["OFF"]

            # =====================================================================
            # 4) 유급휴무
            #    - 기록 없음: PAY
            #    - 기록 있음: ERROR
            # =====================================================================
            elif cat == "유급휴무":
                status_codes = ["ERROR"] if (has_checkin or has_checkout) else ["PAY"]

            # =====================================================================
            # 5) 무급휴무
            #    - 기록 없음: NOPAY
            #    - 기록 있음: ERROR
            # =====================================================================
            elif cat == "무급휴무":
                status_codes = ["ERROR"] if (has_checkin or has_checkout) else ["NOPAY"]

            # 기타 방어
            else:
                status_codes = ["NOSCHEDULE"]

    # 라벨(사람 읽기용)
    status_label = "+".join(STATUS_LABELS.get(c, c) for c in status_codes)
    status_label_list = [STATUS_LABELS.get(c, c) for c in status_codes]

    return Metrics(
        late_seconds=late_seconds,
        early_seconds=early_seconds,
        overtime_seconds=overtime_seconds,
        holiday_seconds=holiday_seconds,
        status=status_label,
        status_codes=status_codes,
        status_labels=status_label_list,
    )