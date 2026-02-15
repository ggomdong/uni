from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from django.utils import timezone


def resolve_month_input(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    if len(v) == 7 and v[4] == "-":
        return v.replace("-", "")
    if len(v) == 6 and v.isdigit():
        return v
    return None


def month_range(ym: str) -> tuple[date, date]:
    year = int(ym[:4])
    month = int(ym[4:6])
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def parse_used_date(value: str | None) -> tuple[date | None, str | None]:
    if not value:
        return None, "사용일은 필수입니다."
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except ValueError:
        return None, "사용일은 YYYY-MM-DD 형식이어야 합니다."


def parse_amount(value, field_name: str) -> tuple[int | None, str | None]:
    if value is None or value == "":
        return None, f"{field_name}는 필수입니다."
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name}는 숫자여야 합니다."
    if amount <= 0:
        return None, f"{field_name}는 0보다 커야 합니다."
    return amount, None


def normalize_ym_strict(value: str | None, *, default_to_now: bool = True) -> tuple[str | None, str | None]:
    if not value:
        if default_to_now:
            return timezone.now().strftime("%Y%m"), None
        return None, "ym은 YYYY-MM 또는 YYYYMM 형식이어야 합니다."

    ym = resolve_month_input(value)
    if ym is None:
        return None, "ym은 YYYY-MM 또는 YYYYMM 형식이어야 합니다."
    return ym, None


def normalize_ym_or_now(value: str | None) -> str:
    ym, error = normalize_ym_strict(value, default_to_now=True)
    if error or ym is None:
        return timezone.now().strftime("%Y%m")
    return ym


def normalize_ym(value: str | None, *, default_to_now: bool = True) -> tuple[str | None, str | None]:
    return normalize_ym_strict(value, default_to_now=default_to_now)
