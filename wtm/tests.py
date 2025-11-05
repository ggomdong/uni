# wtm/tests.py
from datetime import date, datetime, time
from types import SimpleNamespace
from django.test import SimpleTestCase

from wtm.attendance_calc import (
    to_dt, make_paid_segments, total_minutes,
    minutes_before, minutes_after, intersection_minutes, compute_overtime_minutes
)

def module(
    start="09:00", end="18:00",
    r1s="12:00", r1e="13:00",
    r2s=None, r2e=None,
    cat="정규근무", name="일반근무", color=1
):
    return SimpleNamespace(
        start_time=start, end_time=end,
        rest1_start_time=r1s, rest1_end_time=r1e,
        rest2_start_time=r2s, rest2_end_time=r2e,
        cat=cat, name=name, color=color
    )

def dt(d: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(d, time(h, m))

class AttendanceCalcTests(SimpleTestCase):
    def test_make_paid_segments_basic(self):
        d = date(2025, 10, 3)
        m = module()  # 09~18, 휴게 12~13
        segs = make_paid_segments(d, m)
        self.assertEqual(len(segs), 2)
        self.assertEqual(total_minutes(segs), 480)  # 8시간

    def test_late_after_lunch(self):
        d = date(2025, 10, 3)
        paid = make_paid_segments(d, module())  # 09~12, 13~18
        self.assertEqual(minutes_before(dt(d, "14:00"), paid), 240)
        # 09~12(180) + 13~14(60)

    def test_early_leave_simple(self):
        d = date(2025, 10, 3)
        paid = make_paid_segments(d, module())  # 09~12, 13~18
        self.assertEqual(minutes_after(dt(d, "17:30"), paid), 30)

    def test_holiday_intersection(self):
        d = date(2025, 10, 5)
        paid = make_paid_segments(d, module(cat="휴일근무"))
        # 10:00~19:00 체류 -> 10~12(120) + 13~18(300) = 420
        self.assertEqual(intersection_minutes(dt(d, "10:00"), dt(d, "19:00"), paid), 420)

    def test_overtime(self):
        d = date(2025, 10, 3)
        paid = make_paid_segments(d, module())
        overtime = compute_overtime_minutes(dt(d, "19:00"), paid)
        self.assertEqual(overtime, 60)

    def test_no_schedule_day(self):
        d = date(2025, 10, 4)
        # module = None 가정 → 뷰에서 NOSCHEDULE 처리 (뷰 단 테스트에서 확인)

    def test_off_day_paid_is_zero(self):
        # OFF/유급/무급 휴무는 paid_segments가 비거나, 지표는 0이 맞는지(뷰 단 논리)
        pass

    def test_checkin_only_no_checkout(self):
        d = date(2025, 10, 3)
        paid = make_paid_segments(d, module())
        # late는 계산 가능하지만 early/overtime은 0인지 확인
        assert minutes_after(None, paid) == 0

    def test_checkout_only_no_checkin(self):
        d = date(2025, 10, 3)
        paid = make_paid_segments(d, module())
        assert minutes_before(None, paid) == 0

    def test_two_breaks_overlap_case(self):
        d = date(2025, 10, 3)
        m = module(r1s="11:30", r1e="12:30", r2s="12:00", r2e="13:00")
        assert total_minutes(make_paid_segments(d, m)) == 450

    def test_break_outside_work_ignored(self):
        d = date(2025, 10, 3)
        # r1을 근무 밖(06~07)으로, 점심(12~13)은 r2로 유지
        m = module(r1s="06:00", r1e="07:00", r2s="12:00", r2e="13:00")
        assert total_minutes(make_paid_segments(d, m)) == 480

    def test_two_breaks_21h_with_late_and_early(self):
        d = date(2025, 10, 3)
        m = module(end="21:00", r2s="18:00", r2e="18:30")
        paid = make_paid_segments(d, m)
        # 세그먼트 3개
        self.assertEqual(
            [(a.strftime("%H:%M"), b.strftime("%H:%M")) for a, b in paid],
            [("09:00", "12:00"), ("13:00", "18:00"), ("18:30", "21:00")]
        )
        self.assertEqual(total_minutes(paid), 630)
        # 17:30 조퇴 = 17:30~18:00(30) + 18:30~21:00(150) = 180
        self.assertEqual(minutes_after(dt(d, "17:30"), paid), 180)
        # 10:00~19:00 교집합 = 450
        self.assertEqual(intersection_minutes(dt(d, "10:00"), dt(d, "19:00"), paid), 450)
        # 연장: 21:00이 마지막이므로 19:00 퇴근이면 0
        overtime = compute_overtime_minutes(dt(d, "19:00"), paid)
        self.assertEqual(overtime, 0)

