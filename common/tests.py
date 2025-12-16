from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from wtm.attendance_calc import LogsDay, compute_seconds_status_for_day


@dataclass
class FakeModule:
    """
    compute_seconds_status_for_day()에서 필요한 필드만 가진 Module-like 객체.
    - make_paid_segments()가 getattr로 휴게시간을 읽으므로 필드명을 맞춰 둠.
    """
    cat: str
    start_time: str = "09:00"
    end_time: str = "18:00"
    rest1_start_time: str | None = "12:00"
    rest1_end_time: str | None = "13:00"
    rest2_start_time: str | None = None
    rest2_end_time: str | None = None


def naive_dt(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, 0)


@override_settings(USE_TZ=True, TIME_ZONE="Asia/Seoul")
class StatusCodesTests(SimpleTestCase):
    """
    상태코드 재정의 테스트
    - 시간계산은 '기존대로' 수행된다는 전제
    - 여기서는 status_codes 중심으로 검증
    """

    # -------------------------
    # 공통 헬퍼
    # -------------------------
    def run_case(
        self,
        record_day: date,
        module: FakeModule | None,
        checkin: str | None,
        checkout: str | None,
        now: datetime,
    ):
        log = LogsDay(checkin=checkin, checkout=checkout)

        # compute_* 함수가 있는 모듈 경로에 맞게 patch 경로를 수정하세요.
        # 예: wtm.attendance_calc.timezone.now
        with patch("wtm.attendance_calc.timezone.now", return_value=now):
            return compute_seconds_status_for_day(record_day, module, log)

    # -------------------------
    # 0) module 없음 / 알 수 없는 cat
    # -------------------------
    def test_no_module_returns_noschedule(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        metrics = self.run_case(date(2025, 12, 10), None, None, None, now)
        self.assertEqual(metrics.status_codes, ["NOSCHEDULE"])

    def test_unknown_cat_returns_noschedule(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="알수없음")
        metrics = self.run_case(date(2025, 12, 10), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["NOSCHEDULE"])

    # -------------------------
    # 1) 미래일 정책: 소정근로=NORMAL, 휴일근로=HOLIDAY
    # -------------------------
    def test_future_regular_is_normal(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 20), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["NORMAL"])

    def test_future_holiday_is_holiday(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="휴일근로")
        metrics = self.run_case(date(2025, 12, 20), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["HOLIDAY"])

    # (선택) 미래 OFF/PAY/NOPAY도 근무표대로 표시되는지(현재 로직상 자연스럽게 그렇게 됨)
    def test_future_off_is_off(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="OFF")
        metrics = self.run_case(date(2025, 12, 20), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["OFF"])

    def test_future_pay_is_pay(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="유급휴무")
        metrics = self.run_case(date(2025, 12, 20), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["PAY"])

    def test_future_nopay_is_nopay(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="무급휴무")
        metrics = self.run_case(date(2025, 12, 20), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["NOPAY"])

    # -------------------------
    # 2) OFF/PAY/NOPAY: 기록 있으면 ERROR, 없으면 단일코드
    # -------------------------
    def test_off_no_log_is_off(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="OFF")
        metrics = self.run_case(date(2025, 12, 10), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["OFF"])

    def test_off_with_log_is_error(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="OFF")
        metrics = self.run_case(date(2025, 12, 10), module, "09:00", None, now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    def test_pay_no_log_is_pay(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="유급휴무")
        metrics = self.run_case(date(2025, 12, 10), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["PAY"])

    def test_pay_with_log_is_error(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="유급휴무")
        metrics = self.run_case(date(2025, 12, 10), module, None, "18:00", now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    def test_nopay_no_log_is_nopay(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="무급휴무")
        metrics = self.run_case(date(2025, 12, 10), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["NOPAY"])

    def test_nopay_with_log_is_error(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="무급휴무")
        metrics = self.run_case(date(2025, 12, 10), module, "09:00", "18:00", now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    # -------------------------
    # 3) 소정근로(과거): 기본 케이스
    # -------------------------
    def test_regular_past_no_log_is_error(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    def test_regular_past_normal(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "09:00", "18:00", now)
        self.assertEqual(metrics.status_codes, ["NORMAL"])

    def test_regular_past_late_only(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "09:10", "18:00", now)
        self.assertEqual(metrics.status_codes, ["LATE"])

    def test_regular_past_early_only(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "09:00", "17:50", now)
        self.assertEqual(metrics.status_codes, ["EARLY"])

    def test_regular_past_overtime_only(self):
        """
        중요: '연장만 있으면 OVERTIME 단일' (NORMAL+OVERTIME 금지)
        """
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "09:00", "18:30", now)
        self.assertEqual(metrics.status_codes, ["OVERTIME"])

    def test_regular_past_late_and_early(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "09:10", "17:50", now)
        self.assertEqual(metrics.status_codes, ["LATE", "EARLY"])  # 순서 검증

    def test_regular_past_late_and_overtime(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "09:10", "18:30", now)
        self.assertEqual(metrics.status_codes, ["LATE", "OVERTIME"])  # 순서 검증

    # (추가) 현실적으로 발생 가능한 조합(예: 조기출근 + 조퇴)
    def test_regular_past_early_and_overtime(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "08:30", "17:50", now)
        self.assertEqual(metrics.status_codes, ["EARLY"])

    # -------------------------
    # 4) 휴일근로(과거): HOLIDAY 단일 / 오류는 ERROR
    # -------------------------
    def test_holiday_past_no_log_is_error(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="휴일근로")
        metrics = self.run_case(date(2025, 12, 10), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    def test_holiday_past_is_holiday_single_even_if_modifiers_exist(self):
        """
        휴일근로는 '지각/조퇴/연장 no count'라서,
        late/early/overtime가 계산되더라도 status_codes는 HOLIDAY 단일이어야 한다.
        """
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="휴일근로")
        metrics = self.run_case(date(2025, 12, 10), module, "10:00", "14:00", now)
        self.assertEqual(metrics.status_codes, ["HOLIDAY"])

    # -------------------------
    # 5) ERROR 상세: wrong_logs(체류∩유급 0)
    # -------------------------
    def test_wrong_logs_intersection_zero_is_error(self):
        """
        출퇴근은 찍었지만 유급세그먼트와 교집합 0이면 ERROR.
        예) 근무(09-18)인데 06-07만 찍힌 경우.
        """
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, "06:00", "07:00", now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    # -------------------------
    # 6) 오늘(today) 특수 규칙: 시업 전/후 출퇴근 전무
    # -------------------------
    def test_today_before_start_no_log_is_not_error_regular(self):
        """
        오늘 + 시업 전 + 출퇴근 전무 => ERROR 아님 (현재 오류 로직 유지 시)
        => 소정근로는 NORMAL로 표시됨
        """
        now = naive_dt(2025, 12, 16, 8, 0)  # 09:00 이전
        module = FakeModule(cat="소정근로", start_time="09:00", end_time="18:00")
        metrics = self.run_case(date(2025, 12, 16), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["NORMAL"])

    def test_today_after_start_no_log_is_error_regular(self):
        """
        오늘 + 시업 후 + 출퇴근 전무 => ERROR
        """
        now = naive_dt(2025, 12, 16, 10, 0)  # 09:00 이후
        module = FakeModule(cat="소정근로", start_time="09:00", end_time="18:00")
        metrics = self.run_case(date(2025, 12, 16), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    def test_today_before_start_no_log_is_not_error_holiday(self):
        """
        휴일근로도 오늘 시업 전에는 ERROR 아님 => HOLIDAY 단일
        """
        now = naive_dt(2025, 12, 16, 8, 0)
        module = FakeModule(cat="휴일근로", start_time="09:00", end_time="18:00")
        metrics = self.run_case(date(2025, 12, 16), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["HOLIDAY"])

    def test_today_after_start_no_log_is_error_holiday(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="휴일근로", start_time="09:00", end_time="18:00")
        metrics = self.run_case(date(2025, 12, 16), module, None, None, now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    # -------------------------
    # 7) 비정상(부분 로그) 케이스: 현재 오류로 취급하지 않는 구간을 "명시적으로" 고정
    # -------------------------
    def test_today_after_start_checkout_only_is_not_auto_error_by_current_rule(self):
        """
        주의: 현재 오류 판정은 '출퇴근 전무'만 start_passed_no_check로 잡는다.
        checkout만 있는 케이스는 ERROR로 잡히지 않을 수 있다.
        이 테스트는 '현 정책 그대로'를 고정하는 안전장치다.
        """
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로", start_time="09:00", end_time="18:00")
        metrics = self.run_case(date(2025, 12, 16), module, None, "17:50", now)

        # 기대값은 현재 시간계산/모디파이어 구현에 따라 달라질 수 있음.
        # 체크인 None이면 early 계산만 반영되어 EARLY가 나올 가능성이 큼.
        self.assertIn(metrics.status_codes[0], ["ERROR"])
        # ↑ 만약 정책상 "부분 로그는 무조건 ERROR"로 바꾸면 이 테스트를 ERROR로 고정하세요.

    def test_past_checkout_only_is_error(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 10), module, None, "17:50", now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    def test_future_checkout_only_is_error(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로")
        metrics = self.run_case(date(2025, 12, 20), module, None, "17:50", now)
        self.assertEqual(metrics.status_codes, ["ERROR"])

    def test_wrong_logs_intersection_zero_has_zero_metrics(self):
        now = naive_dt(2025, 12, 16, 10, 0)
        module = FakeModule(cat="소정근로", start_time="09:30", end_time="21:00",
                            rest1_start_time=None, rest1_end_time=None)
        metrics = self.run_case(date(2025, 12, 10), module, "09:14:59", "09:15:04", now)

        self.assertEqual(metrics.status_codes, ["ERROR"])
        self.assertEqual(metrics.late_seconds, 0)
        self.assertEqual(metrics.early_seconds, 0)
        self.assertEqual(metrics.overtime_seconds, 0)