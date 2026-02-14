from __future__ import annotations

from calendar import monthrange
from datetime import date

from common.models import Holiday, Business


def _business_for_month(branch, year: int, month: int):
    last_day = date(year, month, monthrange(year, month)[1])
    return (
        Business.objects.filter(branch=branch, stand_date__lte=last_day)
        .order_by("-stand_date")
        .first()
    )


def _extract_closed_weekdays(business) -> list[int]:
    if business is None:
        return []
    day_codes = [
        (business.mon, 1),
        (business.tue, 2),
        (business.wed, 3),
        (business.thu, 4),
        (business.fri, 5),
        (business.sat, 6),
        (business.sun, 7),
    ]
    return [weekday for code, weekday in day_codes if code != "Y"]


def get_non_business_weekdays(year: int, month: int, *, branch) -> list[int]:
    business = _business_for_month(branch, year, month)
    return _extract_closed_weekdays(business)


def get_non_business_calendar(year: int, month: int, *, branch) -> tuple[set[int], list[int]]:
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    business = _business_for_month(branch, year, month)  # 1회
    closed_weekdays = _extract_closed_weekdays(business)

    holiday_set = set(
        Holiday.objects.filter(branch=branch, holiday__range=(first_day, last_day))
        .values_list("holiday", flat=True)
    )  # 1회

    non_business_days: set[int] = set()
    closed_weekdays_set = set(closed_weekdays)
    for day in range(1, last_day.day + 1):
        d = date(year, month, day)
        weekday = d.isoweekday()  # 1=월, ..., 7=일
        if d in holiday_set or weekday in closed_weekdays_set:
            non_business_days.add(day)

    return non_business_days, closed_weekdays


def get_non_business_days(year: int, month: int, *, branch) -> set[int]:
    non_business_days, _ = get_non_business_calendar(year, month, branch=branch)
    return non_business_days
