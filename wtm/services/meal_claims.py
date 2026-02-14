from __future__ import annotations

from calendar import monthrange
from datetime import date

from django.db.models import Q

from common.models import User
from wtm.models import MealClaim, BranchMonthClose


def _resolve_month_input(month_value: str | None):
    if not month_value:
        return None
    v = month_value.strip()
    if len(v) == 7 and v[4] == "-":
        return v.replace("-", "")
    if len(v) == 6 and v.isdigit():
        return v
    return None


def _resolve_ym(ym: str | None, *, fallback_ym: str):
    if ym and len(ym) == 6 and ym.isdigit():
        return ym
    return fallback_ym


def _month_range(ym: str):
    year = int(ym[:4])
    month = int(ym[4:6])
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _is_month_closed(branch, ym: str):
    return BranchMonthClose.objects.filter(branch=branch, ym=ym, is_closed=True).exists()


def _get_branch_users(branch, used_date: date | None):
    base_qs = User.objects.filter(branch=branch, is_active=True, is_employee=True)
    if used_date:
        base_qs = base_qs.filter(join_date__lte=used_date).filter(
            Q(out_date__isnull=True) | Q(out_date__gte=used_date)
        )
    return base_qs.order_by("emp_name")


def _parse_amount(value: str, field_name: str):
    if value is None or value == "":
        return None, f"{field_name}는 필수입니다."
    try:
        amount = int(value)
    except ValueError:
        return None, f"{field_name}는 숫자여야 합니다."
    if amount <= 0:
        return None, f"{field_name}는 0보다 커야 합니다."
    return amount, None


def _parse_approval_no(value: str | None, *, branch, used_date: date, exclude_claim_id: int | None = None):
    v = (value or "").strip()
    if not v:
        return None, "승인번호는 필수입니다."
    if not v.isdigit():
        return None, "승인번호는 숫자만 입력할 수 있습니다."
    if len(v) != 8:
        return None, "승인번호는 8자리여야 합니다."

    ym = used_date.strftime("%Y%m")
    start_date, end_date = _month_range(ym)

    qs = MealClaim.objects.filter(
        branch=branch,
        approval_no=v,
        is_deleted=False,
        used_date__gte=start_date,
        used_date__lte=end_date,
    )
    if exclude_claim_id is not None:
        qs = qs.exclude(id=exclude_claim_id)

    if qs.exists():
        return None, "동일한 승인번호가 이번 달에 이미 등록되어 있습니다. (날짜 오입력 여부 확인 필요)"
    return v, None


def parse_participants_json(participants_list, branch, used_date: date):
    participants: list[tuple[int, int]] = []
    errors: list[str] = []

    if participants_list is None:
        return participants, ["대상자를 최소 1명 이상 입력해야 합니다."]
    if not isinstance(participants_list, list):
        return participants, ["대상자 정보가 올바르지 않습니다."]

    seen_users = set()
    for raw_item in participants_list:
        if not isinstance(raw_item, dict):
            errors.append("대상자 정보가 올바르지 않습니다.")
            continue
        raw_user_id = raw_item.get("user_id")
        raw_amount = raw_item.get("amount")
        if raw_user_id is None or raw_amount is None:
            errors.append("대상자와 금액을 모두 입력해야 합니다.")
            continue
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            errors.append("대상자 정보가 올바르지 않습니다.")
            continue

        amount, error = _parse_amount(str(raw_amount), "분배금액")
        if error:
            errors.append(error)
            continue
        if user_id in seen_users:
            errors.append("대상자는 중복될 수 없습니다.")
            continue
        seen_users.add(user_id)
        participants.append((user_id, amount))

    if not participants:
        errors.append("대상자를 최소 1명 이상 입력해야 합니다.")
        return participants, errors

    valid_user_ids = set(
        _get_branch_users(branch, used_date)
        .filter(id__in=[uid for uid, _ in participants])
        .values_list("id", flat=True)
    )
    for uid, _ in participants:
        if uid not in valid_user_ids:
            errors.append("지점 소속이 아닌 대상자가 포함되어 있습니다.")
            break

    return participants, errors