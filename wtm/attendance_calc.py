# -----------------------------------------------------------------------------
# 근무/휴게/지각/조퇴/연장 계산의 "핵심 공통 로직".
# - 스케줄(근로모듈)의 "유급 근로 시간대"를 구간(segments)으로 만들고,
# - 실제 체류(출근~퇴근)와의 '구간 연산'으로 각 지표(지각/조퇴/연장/휴일근무)를 계산한다.
#
# ※ 이 모듈은 "순수 함수"들로만 구성되어 있으므로
#    DRF API, Django 템플릿 뷰, 백오피스 커맨드, 배치 등 어디서든 같은 결과를 재사용할 수 있다.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 사용 가이드 (요약)
# -----------------------------------------------------------------------------
# 1) 유급 세그먼트 구성
#    paid = make_paid_segments(record_day, module)
#
# 2) 지각/조퇴/연장/휴일근무 분 계산
#    checkin_dt  = to_dt(record_day, checkin_hhmm)   # 첫 출근 "HH:mm" or None
#    checkout_dt = to_dt(record_day, checkout_hhmm)  # 마지막 퇴근 "HH:mm" or None
#
#    late_minutes        = minutes_before(checkin_dt, paid)          # 지각
#    early_minutes = minutes_after(checkout_dt, paid)          # 조퇴
#    holiday_minutes     = intersection_minutes(checkin_dt, checkout_dt, paid)   # (휴일근무일) 체류∩유급
#
#    last_end = last_paid_end(paid)
#    overtime_minutes = max(0, int((checkout_dt - last_end).total_seconds() // 60)) \
#                       if (checkout_dt and last_end and checkout_dt > last_end) else 0
#
# 3) 결근 판정
#    paid_total     = total_minutes(paid)
#    presence_paid  = intersection_minutes(checkin_dt, checkout_dt, paid) if (checkin_dt and checkout_dt) else 0
#    is_absent      = (paid_total > 0 and presence_paid == 0)
#
# -----------------------------------------------------------------------------
# 설계 메모
# -----------------------------------------------------------------------------
# - 이 로직은 '구간 연산'에 기초한다. 휴게 구간은 유급에서 제외되어 있으므로
#   지각/조퇴 계산 시에도 휴게 시간은 자연스럽게 제외된다.
#   예) 휴게 이후(13:00) 출근이면, 09:00~12:00 + 13:00~출근시각까지의 유급이 모두 지각으로 잡힘.
#
# - 현재는 '하루 단일 출근~퇴근' 전제로 설계했다(earliest IN, latest OUT).
#   중간 외출/재출근까지 정밀히 반영하려면,
#   체류 구간을 여러 세그먼트(예: [(in1,out1),(in2,out2),...])로 받아
#   intersection_minutes()에 차례로 합산하는 확장도 간단히 가능하다.
#
# - 야간/익일 근무(예: 22:00~익일 06:00)는 본 모듈에서 '같은 날' 가정이므로
#   날짜를 분할하여 두 번 계산하거나, day를 교체하는 방식으로 확장해야 한다.
#
# - 본 모듈은 I/O가 전혀 없고 예외를 던지지 않도록 방어되어 있어
#   상위 레이어(API/템플릿/배치)에서 그대로 호출하기 안전하다.
#
# - 성능: 한 달(최대 31일) 단위로 호출해도, 날짜당 몇 개의 구간 연산만 수행하므로 매우 가볍다.

from dataclasses import dataclass
from datetime import datetime, date
from django.utils import timezone
from common.context_processors import STATUS_LABELS
from typing import List, Optional, Sequence, Tuple, TYPE_CHECKING

@dataclass
class LogsDay:
    checkin: Optional[str]             # "HH:mm" (최초)
    checkout: Optional[str]            # "HH:mm" (최종)

@dataclass
class Metrics:
    late_minutes: int
    early_minutes: int
    overtime_minutes: int
    holiday_minutes: int
    status: str
    status_codes: list[str]
    status_labels: list[str]

if TYPE_CHECKING:
    from wtm.models import Module  # 타입체커 전용, 런타임 미임포트

# 시간 표기 포맷(모듈에서 사용하는 HH:mm 형태)
TIME_FMT = "%H:%M"

# 타입 별칭: (start_dt, end_dt) 쌍의 리스트
Segment = Tuple[datetime, datetime]


def compute_minutes_status_for_day(record_day: date, module: "Module | None", log: LogsDay) -> Metrics:
    """
    기존 순수 함수들(to_dt/make_paid_segments/minutes_*)만 조합한 '얇은 코어'.
    - DB 접근 없음
    - 정책 변경 시 이 함수 하나만 고치면, 앱/웹/인덱스 전 화면에 동일 적용
    """
    ######### 공통 ##########

    # 1) 휴게 반영 유급 세그먼트 생성
    paid_segments = make_paid_segments(record_day, module)
    paid_total = total_minutes(paid_segments)  # 유급세그먼트 총 분

    # 2) 출퇴근 dt
    checkin_dt  = to_dt(record_day, log.checkin)
    checkout_dt = to_dt(record_day, log.checkout)

    ######### 시간 계산 ##########

    # 1) 지각/조퇴
    late_minutes  = minutes_before(checkin_dt,  paid_segments)
    early_minutes = minutes_after(checkout_dt, paid_segments)

    # 2) 연장
    overtime_minutes = compute_overtime_minutes(checkin_dt, checkout_dt, paid_segments)

    # 3) 휴일근무
    holiday_minutes = 0
    if module and module.cat == "휴일근무" and checkin_dt and checkout_dt:
        holiday_minutes = intersection_minutes(checkin_dt, checkout_dt, paid_segments)

    ######### 상태 정의 ##########

    #=== 상태코드 조합 산출 ===
    has_checkin = bool(checkin_dt)
    has_checkout = bool(checkout_dt)
    # 실 체류 ∩ 유급
    presence_paid = intersection_minutes(checkin_dt, checkout_dt, paid_segments) if (
                has_checkin and has_checkout) else 0

    # 오늘 이후의 상태 판정을 위한 변수 설정
    today = timezone.now().date()
    is_today = (record_day == today)
    is_future = (record_day > today)

    if not module:
        status_codes = ["NOSCHEDULE"]
    else:
        cat = module.cat

        # 1) 휴무/오프/스케줄 있는 날 먼저 처리
        if cat in ("유급휴무", "무급휴무", "OFF"):
            # 출퇴근 기록 있으면 오류
            if has_checkin or has_checkout:
                status_codes = ["ERROR"]
            else:
                base_map = {"유급휴무": "PAY", "무급휴무": "NOPAY", "OFF": "OFF"}
                status_codes = [base_map[cat]]

        elif cat in ("정규근무", "휴일근무"):

            if is_future:
                # 미래: 휴일근무 외에는 아직 결정되지 않음(칩/점 미표시용으로 빈 배열)
                status_codes = []
                if cat == "휴일근무":
                    status_codes.append("HOLIDAY")

            else:
                if is_today:
                    # 오늘: '명백히 잘못'이면 ERROR
                    is_error = (
                        (has_checkin and has_checkout and paid_total > 0 and presence_paid == 0)
                    )
                else:
                    is_error = (
                        # (1) 출퇴근 기록 없음
                            (not has_checkin and not has_checkout) or
                            # (2) 유급 교집합 0
                            (paid_total > 0 and has_checkin and has_checkout and presence_paid == 0)
                    )

                if is_error:
                    status_codes = ["ERROR"]
                else:
                    status_codes = []
                    # 휴일근무면, "휴일근무" 상태 설정, 정규근무는 "정규근무"라고 설정하지 않음
                    if cat == "휴일근무":
                        status_codes.append("HOLIDAY")

                    # 모디파이어
                    if late_minutes > 0:
                        status_codes.append("LATE")
                    if early_minutes > 0:
                        status_codes.append("EARLY")
                    if overtime_minutes > 0:
                        status_codes.append("OVERTIME")

                    # 정규근무에서 '정상' 부여 규칙
                    # - 지각/조퇴가 없으면 NORMAL 추가
                    # - '정상 + 연장' 케이스 허용을 위해, 연장이 있더라도 NORMAL은 함께 둘 수 있음(이때 NORMAL을 앞으로 두어 정렬처리)
                    if cat == "정규근무" and has_checkin and ("LATE" not in status_codes) and ("EARLY" not in status_codes):
                        status_codes.insert(0, "NORMAL")

        else:
            # 카테고리 정의 외 방어
            status_codes = ["NOSCHEDULE"]

    # 라벨(사람 읽기용)
    status_label = "+".join(STATUS_LABELS.get(c, c) for c in status_codes)
    status_label_list = [STATUS_LABELS.get(c, c) for c in status_codes]

    return Metrics(
        late_minutes=late_minutes,
        early_minutes=early_minutes,
        overtime_minutes=overtime_minutes,
        holiday_minutes=holiday_minutes,
        status=status_label,
        status_codes=status_codes,
        status_labels=status_label_list,
    )


def to_dt(day: date, hhmm: Optional[str]) -> Optional[datetime]:
    """
        "2025-10-03" (date) + "HH:mm" (string) -> datetime 조합.

        Parameters
        ----------
        day : date
            '해당 근무일' 날짜. timezone-naive 로 취급(서버/현지 규칙 고정).
        hhmm : Optional[str]
            "HH:mm" 또는 None/"-". None/"-"는 유효하지 않은 시각으로 간주.

        Returns
        -------
        Optional[datetime]
            유효한 경우 datetime, 그 외에는 None.

        Notes
        -----
        - 본 모듈은 '하루 안'에서의 계산을 가정(야간 근무 등 날짜 경계는 별도 정책 필요).
          필요 시 day를 적절히 바꿔 두 번 계산(예: 22:00~24:00, 00:00~06:00)하는 방식으로 확장 가능.
        """
    if not hhmm or hhmm == "-":
        return None
    return datetime.combine(day, datetime.strptime(hhmm, TIME_FMT).time())


def make_paid_segments(day: date, module: "Module") -> List[Segment]:
    """
    하나의 모듈(근무표상 스케줄)에서 '유급 근로 세그먼트' 리스트를 생성.

    아이디어
    --------
    - '근무 전체 구간' = (start_time ~ end_time)
    - '휴게 구간' = (rest1_start ~ rest1_end), (rest2_start ~ rest2_end) [0~2개]
    - 유급 근로 세그먼트 = 근무 전체 구간에서 모든 휴게 구간을 '빼기'
      => 결과는 서로 겹치지 않는 [ (S1,E1), (S2,E2), ... ] 형태

    Parameters
    ----------
    day : date
        해당 일자(record_day)
    module : Module-like
        다음 속성을 가진 객체(wtm.models.Module과 동일 전제)
        - start_time, end_time: "HH:mm" 혹은 "-"(빈 의미)
        - rest1_start_time, rest1_end_time (optional)
        - rest2_start_time, rest2_end_time (optional)

    Returns
    -------
    List[Segment]
        유효한 (start_dt, end_dt) 쌍의 리스트. (end > start) 만 포함.

    Edge Cases & 방어 로직
    ----------------------
    - start/end 가 비어있거나 "-"이면 [] 반환
    - 휴게 구간이 근무 전체와 전혀 겹치지 않으면 무시
    - 휴게 구간이 근무 구간을 부분/전체로 덮는 경우도 자연스럽게 잘려나감
    - 휴게 구간의 순서/겹침은 정렬/클리핑으로 정리
    """

    # 근무 구간 파싱
    if not module or not module.start_time or not module.end_time \
       or module.start_time == "-" or module.end_time == "-":
        return []

    S = to_dt(day, module.start_time)
    E = to_dt(day, module.end_time)
    # 비정상 혹은 0분 근무는 유급세그먼트 없음
    if not S or not E or E <= S:
        return []

    # 휴게 구간 파싱(있으면 추가)
    rests: List[Segment] = []
    r1s, r1e = to_dt(day, getattr(module, "rest1_start_time", None)), to_dt(day, getattr(module, "rest1_end_time", None))
    r2s, r2e = to_dt(day, getattr(module, "rest2_start_time", None)), to_dt(day, getattr(module, "rest2_end_time", None))
    if r1s and r1e and r1e > r1s: rests.append((r1s, r1e))
    if r2s and r2e and r2e > r2s: rests.append((r2s, r2e))

    # 1) 근무 전체에서 시작
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


def total_minutes(segments: Sequence[Segment]) -> int:
    """
    구간 리스트의 총 분(minute) 합산.

    Examples
    --------
    # [(09:00~12:00), (13:00~18:00)] => 8시간 = 480분
    total_minutes([(dt(9,0), dt(12,0)), (dt(13,0), dt(18,0))]) == 480
    """
    return sum(int((b - a).total_seconds() // 60) for a, b in segments if b > a)


def minutes_before(t: Optional[datetime], segments: Sequence[Segment]) -> int:
    """
    시각 t '이전'의 유급 근로 누적 분.
    - '지각(late)' 계산에 사용: 스케줄상의 유급 근로가 시작됐는데, 출근(t)이 그 이후라면
      t 이전의 유급 근로가 모두 지각 분으로 잡힌다.

    Examples
    --------
    유급 세그먼트: [(09:00~12:00), (13:00~18:00)]
    - t=10:30 => 09:00~10:30 (90분)
    - t=14:20 => 09:00~12:00(180) + 13:00~14:20(80) = 260분
    """
    if not t:
        return 0
    parts: List[Segment] = []
    for a, b in segments:
        if t <= a:
            # t가 세그먼트 시작 이전이면 교집합 없음
            continue
        parts.append((a, min(b, t)))
    return total_minutes(parts)


def minutes_after(t: Optional[datetime], segments: Sequence[Segment]) -> int:
    """
    시각 t '이후'의 유급 근로 누적 분.
    - '조퇴(early leave)' 계산에 사용: 스케줄상의 유급 근로가 남아 있는데, 퇴근(t)이 그 이전이라면
      t 이후의 유급 근로가 모두 조퇴 분으로 잡힌다.

    Examples
    --------
    유급 세그먼트: [(09:00~12:00), (13:00~18:00)]
    - t=17:30 => 17:30~18:00 (30분)
    - t=11:00 => 11:00~12:00(60) + 13:00~18:00(300) = 360분
    """
    if not t:
        return 0
    parts: List[Segment] = []
    for a, b in segments:
        if t >= b:
            # t가 세그먼트 끝 이후면 교집합 없음
            continue
        parts.append((max(a, t), b))
    return total_minutes(parts)


def intersection_minutes(a: Optional[datetime], b: Optional[datetime], segments: Sequence[Segment]) -> int:
    """
    체류 구간 [a, b) 과 유급 세그먼트들의 교집합 총 분.
    - '휴일근무(holiday)' 분 계산에 사용: 휴일 스케줄이라면 실제 체류와 유급 근로가 겹친 시간만 인정.
    - 일반 일자에서도 '실제 유급 체류'가 얼마나 있었는지 확인할 때 쓸 수 있음.

    Returns
    -------
    int
        교집합 총 분. a/b가 유효하지 않거나 b<=a면 0.

    Examples
    --------
    유급 세그먼트: [(09:00~12:00), (13:00~18:00)]
    - [10:00~19:00) => 10:00~12:00(120) + 13:00~18:00(300) = 420분
    - [08:00~09:10) => 09:00~09:10(10) = 10분
    """
    if not a or not b or b <= a:
        return 0
    parts: List[Segment] = []
    for s, e in segments:
        # 각 세그먼트와 [a,b) 교집합을 취함
        x, y = max(a, s), min(b, e)
        if y > x:
            parts.append((x, y))
    return total_minutes(parts)


def last_paid_end(segments: Sequence[Segment]) -> Optional[datetime]:
    """
    유급 근로 세그먼트들 중 가장 늦은 '끝' 시각.
    - '연장(overtime)' 계산에 사용: 마지막 유급 종료 이후 실제 퇴근까지의 분.
    """
    return max((e for _, e in segments), default=None)


def compute_overtime_minutes(
    checkin: Optional[datetime],
    checkout: Optional[datetime],
    segments: Sequence[Segment],
) -> int:
    if not checkin or not checkout:
        return 0
    last_end = last_paid_end(segments)
    if not last_end:
        return 0

    # 핵심 가드: 스케줄 유급세그먼트와 실제 근무의 교집합이 0이면 연장 없음
    # (intersection_minutes는 네가 이미 쓰는 순수함수)
    paid_overlap = intersection_minutes(checkin, min(checkout, last_end), segments)
    if paid_overlap == 0:
        return 0

    # 연장 계산 (유예 분 없음)
    if checkout <= last_end:
        return 0
    return int((checkout - last_end).total_seconds() // 60)
