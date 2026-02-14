from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from common.models import User
from wtm.models import Schedule, MealClaim, MealClaimParticipant, BranchMonthClose
from wtm.services.base_users import fetch_base_users_for_month


def _resolve_month_input(value: str | None):
    if not value:
        return None
    v = value.strip()
    if len(v) == 7 and v[4] == "-":
        return v.replace("-", "")
    if len(v) == 6 and v.isdigit():
        return v
    return None


def resolve_month_input(value: str | None) -> str | None:
    return _resolve_month_input(value)


def _month_range(ym: str):
    year = int(ym[:4])
    month = int(ym[4:6])
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def month_range(ym: str):
    return _month_range(ym)


def _is_month_closed(branch, ym: str):
    return BranchMonthClose.objects.filter(branch=branch, ym=ym, is_closed=True).exists()


def is_month_closed(branch, ym: str) -> bool:
    return _is_month_closed(branch, ym)


def _get_branch_users(branch, used_date: date | None):
    base_qs = User.objects.filter(branch=branch, is_active=True, is_employee=True)
    if used_date:
        base_qs = base_qs.filter(join_date__lte=used_date).filter(
            Q(out_date__isnull=True) | Q(out_date__gte=used_date)
        )
    return base_qs.order_by("emp_name")


def get_branch_users(branch, used_date: date | None):
    return _get_branch_users(branch, used_date)


def _parse_amount(value, field_name: str):
    if value is None or value == "":
        return None, f"{field_name}는 필수입니다."
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name}는 숫자여야 합니다."
    if amount <= 0:
        return None, f"{field_name}는 0보다 커야 합니다."
    return amount, None


def parse_amount(value, field_name: str):
    return _parse_amount(value, field_name)


def _parse_approval_no(value, *, branch, used_date: date, exclude_claim_id: int | None = None):
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


def parse_approval_no(value, branch, used_date, exclude_claim_id=None):
    return _parse_approval_no(
        value,
        branch=branch,
        used_date=used_date,
        exclude_claim_id=exclude_claim_id,
    )


def parse_used_date(value: str | None):
    if not value:
        return None, "사용일은 필수입니다."
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except ValueError:
        return None, "사용일은 YYYY-MM-DD 형식이어야 합니다."


def normalize_ym_strict(value: str | None, *, default_to_now: bool = True):
    if not value:
        if default_to_now:
            return timezone.now().strftime("%Y%m"), None
        return None, "ym은 YYYY-MM 또는 YYYYMM 형식이어야 합니다."

    ym = _resolve_month_input(value)
    if ym is None:
        return None, "ym은 YYYY-MM 또는 YYYYMM 형식이어야 합니다."
    return ym, None


def normalize_ym_or_now(value: str | None) -> str:
    ym, error = normalize_ym_strict(value, default_to_now=True)
    if error or ym is None:
        return timezone.now().strftime("%Y%m")
    return ym


def normalize_ym(value: str | None, *, default_to_now: bool = True):
    return normalize_ym_strict(value, default_to_now=default_to_now)


def calculate_user_meal_total(user: User, branch, ym: str) -> int:
    year, month = int(ym[:4]), int(ym[4:6])
    last_day_num = monthrange(year, month)[1]

    end_day_for_meal = last_day_num
    out_date = getattr(user, "out_date", None)
    if out_date and out_date.strftime("%Y%m") == ym:
        end_day_for_meal = min(end_day_for_meal, out_date.day)

    if end_day_for_meal < 1:
        return 0

    rel_fields = [f"d{i}" for i in range(1, 32)]
    schedule = (
        Schedule.objects
        .select_related(*rel_fields)
        .filter(user=user, year=str(year), month=f"{month:02d}", branch=branch)
        .first()
    )
    if not schedule:
        return 0

    total = 0
    for day in range(1, end_day_for_meal + 1):
        module = getattr(schedule, f"d{day}", None)
        amount = getattr(module, "meal_amount", None) if module else None
        if amount:
            total += int(amount)
    return total


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

        amount, error = _parse_amount(raw_amount, "분배금액")
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


def parse_participants_form(post_data, branch, used_date: date):
    user_ids = post_data.getlist("participant_user")
    amounts = post_data.getlist("participant_amount")
    participants = []
    errors = []

    if len(user_ids) != len(amounts):
        return participants, ["대상자 정보가 올바르지 않습니다."]

    raw_items = []
    for raw_user_id, raw_amount in zip(user_ids, amounts):
        if not raw_user_id and not raw_amount:
            continue
        if not raw_user_id or not raw_amount:
            errors.append("대상자와 금액을 모두 입력해야 합니다.")
            continue
        raw_items.append({"user_id": raw_user_id, "amount": raw_amount})

    if errors:
        return participants, errors

    participants, parse_errors = parse_participants_json(raw_items, branch, used_date)
    if parse_errors:
        return participants, parse_errors
    return participants, []


def parse_claim_payload(data, branch, *, exclude_claim_id=None):
    errors = []
    used_date_str = data.get("used_date")
    amount_raw = data.get("amount")
    merchant_name = (data.get("merchant_name") or "").strip()

    if not used_date_str or amount_raw in (None, ""):
        errors.append("사용일과 총액은 필수입니다.")
        return None, errors
    if not merchant_name:
        errors.append("가맹점명은 필수입니다.")
        return None, errors

    used_date, error = parse_used_date(used_date_str)
    if error:
        errors.append(error)
        return None, errors

    amount, error = parse_amount(amount_raw, "총액")
    if error:
        errors.append(error)
        return None, errors

    approval_no, error = parse_approval_no(
        data.get("approval_no"),
        branch=branch,
        used_date=used_date,
        exclude_claim_id=exclude_claim_id,
    )
    if error:
        errors.append(error)
        return None, errors

    participants, participant_errors = parse_participants_json(
        data.get("participants"),
        branch,
        used_date,
    )
    if participant_errors:
        return None, participant_errors

    if sum(p[1] for p in participants) != amount:
        errors.append("분배 합계가 총액과 일치해야 합니다.")
        return None, errors

    return {
        "used_date": used_date,
        "amount": amount,
        "approval_no": approval_no,
        "merchant_name": merchant_name,
        "participants": participants,
    }, []


def parse_claim_payload_form(post_data, branch, *, exclude_claim_id=None):
    errors = []
    used_date_str = post_data.get("used_date")
    amount_raw = post_data.get("amount")
    merchant_name = (post_data.get("merchant_name") or "").strip()

    if not used_date_str or amount_raw in (None, ""):
        errors.append("사용일과 총액은 필수입니다.")
        return None, errors
    if not merchant_name:
        errors.append("가맹점명은 필수입니다.")
        return None, errors

    used_date, error = parse_used_date(used_date_str)
    if error:
        errors.append(error)
        return None, errors

    amount, error = parse_amount(amount_raw, "총액")
    if error:
        errors.append(error)
        return None, errors

    approval_no, error = parse_approval_no(
        post_data.get("approval_no"),
        branch=branch,
        used_date=used_date,
        exclude_claim_id=exclude_claim_id,
    )
    if error:
        errors.append(error)
        return None, errors

    participants, participant_errors = parse_participants_form(post_data, branch, used_date)
    if participant_errors:
        return None, participant_errors

    if sum(p[1] for p in participants) != amount:
        errors.append("분배 합계가 총액과 일치해야 합니다.")
        return None, errors

    return {
        "used_date": used_date,
        "amount": amount,
        "approval_no": approval_no,
        "merchant_name": merchant_name,
        "participants": participants,
    }, []


def calculate_meal_totals_for_user_ids(
    user_ids: list[int],
    branch,
    ym: str,
    *,
    out_ymd_map: dict[int, str | None] | None = None,
) -> dict[int, int]:
    if not user_ids:
        return {}

    year, month = int(ym[:4]), int(ym[4:6])
    last_day_num = monthrange(year, month)[1]
    out_ymd_map = out_ymd_map or {}

    rel_fields = [f"d{i}" for i in range(1, 32)]
    schedules = (
        Schedule.objects
        .select_related(*rel_fields)
        .filter(user_id__in=user_ids, year=str(year), month=f"{month:02d}", branch=branch)
    )
    schedule_map = {s.user_id: s for s in schedules}

    totals: dict[int, int] = {}
    for uid in user_ids:
        sch = schedule_map.get(uid)
        if not sch:
            totals[uid] = 0
            continue

        end_day_for_meal = last_day_num
        out_ymd = out_ymd_map.get(uid)
        if out_ymd and out_ymd[:6] == ym:
            end_day_for_meal = min(end_day_for_meal, int(out_ymd[6:8]))

        total = 0
        for day in range(1, end_day_for_meal + 1):
            module = getattr(sch, f"d{day}", None)
            amount = getattr(module, "meal_amount", None) if module else None
            if amount:
                total += int(amount)
        totals[uid] = total

    return totals


def create_claim(user, branch, payload):
    ym = payload["used_date"].strftime("%Y%m")
    if _is_month_closed(branch, ym):
        raise ValueError("마감된 월은 등록할 수 없습니다.")

    with transaction.atomic():
        claim = MealClaim.objects.create(
            branch=branch,
            user=user,
            used_date=payload["used_date"],
            amount=payload["amount"],
            approval_no=payload["approval_no"],
            merchant_name=payload["merchant_name"],
        )
        MealClaimParticipant.objects.bulk_create([
            MealClaimParticipant(claim=claim, user_id=user_id, amount=amount_value)
            for user_id, amount_value in payload["participants"]
        ])
    return claim


def update_claim(branch, claim_id, payload):
    with transaction.atomic():
        claim = MealClaim.objects.select_for_update().get(id=claim_id, branch=branch, is_deleted=False)
        current_ym = claim.used_date.strftime("%Y%m")
        next_ym = payload["used_date"].strftime("%Y%m")

        if _is_month_closed(branch, current_ym) or _is_month_closed(branch, next_ym):
            raise ValueError("마감된 월은 수정할 수 없습니다.")

        claim.used_date = payload["used_date"]
        claim.amount = payload["amount"]
        claim.approval_no = payload["approval_no"]
        claim.merchant_name = payload["merchant_name"]
        claim.save()
        MealClaimParticipant.objects.filter(claim=claim).delete()
        MealClaimParticipant.objects.bulk_create([
            MealClaimParticipant(claim=claim, user_id=user_id, amount=amount_value)
            for user_id, amount_value in payload["participants"]
        ])
    return claim


def soft_delete_claim(branch, claim_id: int):
    claim = MealClaim.objects.get(id=claim_id, branch=branch, is_deleted=False)
    ym = claim.used_date.strftime("%Y%m")
    if _is_month_closed(branch, ym):
        raise ValueError("마감된 월은 삭제할 수 없습니다.")
    claim.is_deleted = True
    claim.save()
    return ym


def serialize_claim_detail(claim, request_user):
    ym = claim.used_date.strftime("%Y%m")
    base_users = fetch_base_users_for_month(ym, branch=claim.branch, is_contract_checked=False)
    base_map = {u["user_id"]: u for u in base_users}

    participants = list(claim.participants.all())
    participants.sort(key=lambda p: (p.user.emp_name or "", p.user_id))
    payload_participants = []
    for p in participants:
        user = p.user
        base_user = base_map.get(user.id, {})
        dept = user.dept or base_user.get("dept", "")
        position = user.position or base_user.get("position", "")
        payload_participants.append({
            "user_id": user.id,
            "emp_name": user.emp_name,
            "dept": dept or "",
            "position": position or "",
            "amount": p.amount,
        })

    can_edit = claim.user_id == request_user.id
    return {
        "id": claim.id,
        "ym": ym,
        "used_date": claim.used_date.strftime("%Y-%m-%d"),
        "merchant_name": claim.merchant_name,
        "approval_no": claim.approval_no,
        "amount": claim.amount,
        "created_by": {"id": claim.user_id, "emp_name": claim.user.emp_name},
        "participants": payload_participants,
        "can_edit": can_edit,
        "can_delete": can_edit,
    }


def claim_participants_summary_for_user(claim, user_id):
    participants = list(claim.participants.all())
    participant_sum = sum(p.amount for p in participants)
    my_amount = next((p.amount for p in participants if p.user_id == user_id), 0)
    participants_count = len(participants)
    return my_amount, participant_sum, participants_count
