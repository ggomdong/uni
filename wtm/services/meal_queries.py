from __future__ import annotations

from django.db.models import Count, Sum

from common.models import User
from wtm.models import MealClaim, MealClaimParticipant
from wtm.services.base_users import fetch_base_users_for_month
from wtm.services.branch_access import is_month_closed
from wtm.services.date_utils import month_range, normalize_ym_or_now
from wtm.services.meal_claims import calculate_meal_totals_for_user_ids


def build_meal_status_rows(stand_ym: str | None, *, branch) -> tuple[str, list[dict]]:
    stand_ym = normalize_ym_or_now(stand_ym)

    # 1) 대상자 : 전 직원
    base_users = fetch_base_users_for_month(stand_ym, branch=branch, is_contract_checked=False)
    if not base_users:
        return stand_ym, []

    uid_list = [u["user_id"] for u in base_users]

    out_ymd_map = {u["user_id"]: u.get("out_ymd") for u in base_users}
    total_map = calculate_meal_totals_for_user_ids(
        uid_list,
        branch,
        stand_ym,
        out_ymd_map=out_ymd_map,
    )

    # 3) rows 구성
    rows = []
    for u in base_users:
        total = total_map.get(u["user_id"], 0)

        rows.append(
            {
                "user_id": u["user_id"],
                "dept": u["dept"],
                "position": u["position"],
                "emp_name": u["emp_name"],
                "total_amount": total if total > 0 else None,  # 0이면 '-'로 보이게
                "used_amount": None,
                "balance": None,
            }
        )

    return stand_ym, rows


def build_meal_usage_summary_map(ym: str, *, branch) -> dict[int, dict]:
    start_date, end_date = month_range(ym)
    summaries = (
        MealClaimParticipant.objects.filter(
            claim__branch=branch,
            claim__is_deleted=False,
            claim__used_date__gte=start_date,
            claim__used_date__lte=end_date,
        )
        .values("user_id")
        .annotate(
            claim_count=Count("claim_id", distinct=True),
            personal_amount=Sum("amount"),
            distributed_amount=Sum("claim__amount"),
        )
    )
    return {summary["user_id"]: summary for summary in summaries}


def get_user_month_participants(user_id: int, *, branch, ym: str):
    start_date, end_date = month_range(ym)
    target_user = User.objects.get(id=user_id, branch=branch)

    participants = list(
        MealClaimParticipant.objects.select_related("claim", "claim__user")
        .filter(
            user_id=user_id,
            claim__branch=branch,
            claim__is_deleted=False,
            claim__used_date__gte=start_date,
            claim__used_date__lte=end_date,
        )
        .order_by("claim__used_date", "claim__id")
    )
    total_personal = sum(p.amount for p in participants)
    total_claim_amount = sum(p.claim.amount for p in participants)
    return target_user, participants, total_personal, total_claim_amount


def list_month_claims_for_table(*, branch, ym: str):
    start_date, end_date = month_range(ym)
    claims = (
        MealClaim.objects.select_related("user")
        .prefetch_related("participants__user")
        .filter(
            branch=branch,
            is_deleted=False,
            used_date__gte=start_date,
            used_date__lte=end_date,
        )
        .order_by("used_date", "id")
    )
    is_closed = is_month_closed(branch, ym)
    return claims, is_closed


def hydrate_claim_participants(claims):
    for claim in claims:
        participants = list(claim.participants.all())
        claim.participant_count = len(participants)
        claim.participant_sum = sum(p.amount for p in participants)
        claim.participants_list = participants
