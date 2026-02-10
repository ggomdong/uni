import json
from calendar import monthrange
from datetime import datetime, date
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.utils import timezone

from common.models import User
from wtm.models import Schedule, MealClaim, MealClaimParticipant, BranchMonthClose  # Schedule에 d1~d31 FK가 있다고 가정
from .helpers import fetch_base_users_for_month


def build_meal_status_rows(stand_ym: str | None, *, branch):
    stand_ym = stand_ym or timezone.now().strftime("%Y%m")
    year, month = int(stand_ym[:4]), int(stand_ym[4:6])
    last_day_num = monthrange(year, month)[1]

    # 1) 대상자 : 전 직원
    base_users = fetch_base_users_for_month(stand_ym, branch=branch, is_contract_checked=False)
    if not base_users:
        return stand_ym, []

    uid_list = [u["user_id"] for u in base_users]

    # 2) 스케줄을 한 번에 조회 (d1~d31 모듈까지 select_related)
    rel_fields = [f"d{i}" for i in range(1, 32)]
    schedules = (
        Schedule.objects
        .select_related(*rel_fields)
        .filter(user_id__in=uid_list, year=str(year), month=f"{month:02d}", branch=branch)
    )
    schedule_map = {s.user_id: s for s in schedules}

    # 3) rows 구성
    rows = []
    for u in base_users:
        sch = schedule_map.get(u["user_id"])
        total = 0

        # 기본은 말일까지
        end_day_for_meal = last_day_num

        # out_date가 해당 월에 있으면 그 날짜까지만 합산
        out_ymd = u.get("out_ymd")  # 'YYYYMMDD' or None
        if out_ymd and out_ymd[:6] == stand_ym:
            out_day = int(out_ymd[6:8])
            end_day_for_meal = min(end_day_for_meal, out_day)

        if sch and end_day_for_meal >= 1:
            for d in range(1, end_day_for_meal + 1):
                m = getattr(sch, f"d{d}", None)  # Module or None
                amt = getattr(m, "meal_amount", None) if m else None
                if amt:
                    total += int(amt)

        rows.append({
            "user_id": u["user_id"],
            "dept": u["dept"],
            "position": u["position"],
            "emp_name": u["emp_name"],
            "total_amount": total if total > 0 else None,  # 0이면 '-'로 보이게
            "used_amount": None,
            "balance": None,
        })

    return stand_ym, rows


def _build_meal_usage_summary_map(ym: str, *, branch):
    start_date, end_date = _month_range(ym)
    summaries = (
        MealClaimParticipant.objects
        .filter(
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


@login_required(login_url="common:login")
def work_meal_status(request, stand_ym: str | None = None):
    branch = getattr(request, "branch", None)
    if branch is None:
        raise Http404("branch code is required")

    requested_ym = _resolve_month_input(request.GET.get("month")) or request.GET.get("ym") or stand_ym
    stand_ym = _resolve_ym(requested_ym)
    stand_ym, rows = build_meal_status_rows(stand_ym, branch=branch)
    usage_map = _build_meal_usage_summary_map(stand_ym, branch=branch)
    for row in rows:
        summary = usage_map.get(row.get("user_id"))
        personal_amount = summary.get("personal_amount", 0) if summary else 0
        row["claim_count"] = summary.get("claim_count", 0) if summary else 0
        row["personal_amount"] = personal_amount
        row["distributed_amount"] = summary.get("distributed_amount", 0) if summary else 0
        if row.get("total_amount") is not None:
            row["balance"] = row["total_amount"] - personal_amount

    context = {
        "stand_ym": stand_ym,
        "month_value": f"{stand_ym[:4]}-{stand_ym[4:]}",
        "rows": rows,
        "active_metric": "meal",  # 메뉴 하이라이트/탭 구분용(선택)
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "tw/wtm/meal/_work_meal_status_table.html", context)

    return render(request, "tw/wtm/work_meal_status.html", context)


@login_required(login_url="common:login")
def work_meal_status_user_modal(request, user_id: int):
    branch = _get_branch_or_404(request)
    requested_ym = _resolve_month_input(request.GET.get("month")) or request.GET.get("ym")
    stand_ym = _resolve_ym(requested_ym)
    start_date, end_date = _month_range(stand_ym)
    try:
        target_user = User.objects.get(id=user_id, branch=branch)
    except User.DoesNotExist:
        raise Http404("user not found")

    participants = list(
        MealClaimParticipant.objects
        .select_related("claim", "claim__user")
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
    return render(request, "tw/wtm/meal/_meal_user_detail_modal.html", {
        "stand_ym": stand_ym,
        "month_value": f"{stand_ym[:4]}-{stand_ym[4:]}",
        "user": target_user,
        "participants": participants,
        "total_personal": total_personal,
        "total_claim_amount": total_claim_amount,
    })


@login_required(login_url="common:login")
def work_meal_modal_close(request):
    return render(request, "tw/wtm/meal/_modal_slot_empty.html")


def _get_branch_or_404(request):
    branch = getattr(request, "branch", None) or getattr(request.user, "branch", None)
    if branch is None:
        raise Http404("branch code is required")
    return branch


def _resolve_ym(ym: str | None):
    if not ym or len(ym) != 6 or not ym.isdigit():
        return timezone.now().strftime("%Y%m")
    return ym


def _resolve_month_input(month_value: str | None):
    if not month_value:
        return None
    if len(month_value) == 7 and month_value[4] == "-":
        return month_value.replace("-", "")
    if len(month_value) == 6 and month_value.isdigit():
        return month_value
    return None


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
        base_qs = base_qs.filter(
            join_date__lte=used_date
        ).filter(
            Q(out_date__isnull=True) | Q(out_date__gte=used_date)
        )
    return (
        base_qs
        .order_by("emp_name")
    )


def _annotate_claim_participants(claims):
    for claim in claims:
        participants = list(claim.participants.all())
        claim.participant_count = len(participants)
        claim.participant_sum = sum(p.amount for p in participants)
        claim.participants_list = participants


def _render_meal_table(request, branch, ym: str):
    start_date, end_date = _month_range(ym)
    claims = (
        MealClaim.objects
        .select_related("user")
        .prefetch_related("participants__user")
        .filter(branch=branch, is_deleted=False, used_date__gte=start_date, used_date__lte=end_date)
        .order_by("used_date", "id")
    )
    _annotate_claim_participants(claims)
    is_closed = _is_month_closed(branch, ym)
    return render(request, "tw/wtm/meal/_meal_table.html", {
        "ym": ym,
        "claims": claims,
        "is_closed": is_closed,
    })


def _render_meal_row(request, claim):
    return render(request, "tw/wtm/meal/_meal_row.html", {
        "claim": claim,
    })


def _render_meal_row_edit(request, claim, branch_users):
    return render(request, "tw/wtm/meal/_meal_row_edit.html", {
        "claim": claim,
        "users": branch_users,
    })


def _parse_approval_no(
    value: str | None,
    *,
    branch,
    used_date: date,
    exclude_claim_id: int | None = None,
):
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


def _parse_participants(post_data, branch, used_date: date):
    user_ids = post_data.getlist("participant_user")
    amounts = post_data.getlist("participant_amount")
    participants = []
    errors = []
    empty_rows = 0
    if len(user_ids) != len(amounts):
        errors.append("대상자 정보가 올바르지 않습니다.")
        return participants, errors

    seen_users = set()
    for raw_user_id, raw_amount in zip(user_ids, amounts):
        if not raw_user_id and not raw_amount:
            empty_rows += 1
            continue
        if not raw_user_id or not raw_amount:
            errors.append("대상자와 금액을 모두 입력해야 합니다.")
            continue
        try:
            user_id = int(raw_user_id)
        except ValueError:
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
    if empty_rows:
        errors.append("비어 있는 대상자 행을 제거하거나 입력하세요.")

    valid_user_ids = set(
        _get_branch_users(branch, used_date)
        .filter(id__in=[user_id for user_id, _ in participants])
        .values_list("id", flat=True)
    )
    for user_id, _ in participants:
        if user_id not in valid_user_ids:
            errors.append("지점 소속이 아닌 대상자가 포함되어 있습니다.")
            break

    return participants, errors


@login_required(login_url="common:login")
def meals_index(request):
    branch = _get_branch_or_404(request)
    ym = _resolve_month_input(request.GET.get("month")) or _resolve_ym(request.GET.get("ym"))

    if request.headers.get("HX-Request") == "true":
        return _render_meal_table(request, branch, ym)

    start_date, end_date = _month_range(ym)
    claims = (
        MealClaim.objects
        .select_related("user")
        .prefetch_related("participants__user")
        .filter(branch=branch, is_deleted=False, used_date__gte=start_date, used_date__lte=end_date)
        .order_by("used_date", "id")
    )
    _annotate_claim_participants(claims)
    is_closed = _is_month_closed(branch, ym)
    month_label = f"{ym[:4]}.{ym[4:]}"
    today = date.today()
    if today.strftime("%Y%m") == ym:
        default_used_date = today
    else:
        default_used_date = date(int(ym[:4]), int(ym[4:6]), 1)
    return render(request, "tw/wtm/work_meal.html", {
        "ym": ym,
        "month_label": month_label,
        "month_value": f"{ym[:4]}-{ym[4:]}",
        "used_date_default": default_used_date.strftime("%Y-%m-%d"),
        "claims": claims,
        "is_closed": is_closed,
        "users": _get_branch_users(branch, default_used_date),
    })


@login_required(login_url="common:login")
def meals_new(request):
    branch = _get_branch_or_404(request)
    used_date_str = request.POST.get("used_date")
    amount_str = request.POST.get("amount")
    merchant_name = (request.POST.get("merchant_name") or "").strip()

    if not used_date_str or not amount_str:
        return HttpResponse("사용일과 총액은 필수입니다.", status=400)
    if not merchant_name:
        return HttpResponse("가맹점명은 필수입니다.", status=400)

    try:
        used_date = datetime.strptime(used_date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponse("사용일은 YYYY-MM-DD 형식이어야 합니다.", status=400)

    amount, error = _parse_amount(amount_str, "총액")
    if error:
        return HttpResponse(error, status=400)

    approval_no, err = _parse_approval_no(
        request.POST.get("approval_no"),
        branch=branch,
        used_date=used_date,
        # 신규는 exclude_claim_id 없음
    )
    if err:
        return HttpResponse(err, status=400)

    participants, participant_errors = _parse_participants(request.POST, branch, used_date)
    if participant_errors:
        return HttpResponse("\n".join(participant_errors), status=400)

    # Server-side validation ensures participant sum matches total amount.
    if sum(p[1] for p in participants) != amount:
        return HttpResponse("분배 합계가 총액과 일치해야 합니다.", status=400)

    ym = used_date.strftime("%Y%m")
    if _is_month_closed(branch, ym):
        return HttpResponse("마감된 월은 등록할 수 없습니다.", status=403)

    with transaction.atomic():
        claim = MealClaim.objects.create(
            branch=branch,
            user=request.user,
            used_date=used_date,
            amount=amount,
            approval_no=approval_no,
            merchant_name=merchant_name,
        )
        MealClaimParticipant.objects.bulk_create([
            MealClaimParticipant(claim=claim, user_id=user_id, amount=amount_value)
            for user_id, amount_value in participants
        ])

    # HTMX swaps the table outerHTML after create/delete.
    resp = _render_meal_table(request, branch, ym)
    resp["HX-Trigger"] = json.dumps({"toast": {"message": "등록되었습니다.", "level": "success"}})
    return resp


@login_required(login_url="common:login")
def meals_delete(request, claim_id: int):
    branch = _get_branch_or_404(request)
    try:
        claim = MealClaim.objects.get(id=claim_id, branch=branch, is_deleted=False)
    except MealClaim.DoesNotExist:
        raise Http404("meal claim not found")

    ym = claim.used_date.strftime("%Y%m")
    if _is_month_closed(branch, ym):
        return HttpResponse("마감된 월은 삭제할 수 없습니다.", status=403)

    claim.is_deleted = True
    claim.save()

    resp = _render_meal_table(request, branch, ym)
    resp["HX-Trigger"] = json.dumps({"toast": {"message": "삭제되었습니다.", "level": "success"}})
    return resp


@login_required(login_url="common:login")
def meals_row(request, claim_id: int):
    branch = _get_branch_or_404(request)
    try:
        claim = (
            MealClaim.objects
            .select_related("user")
            .prefetch_related("participants__user")
            .get(id=claim_id, branch=branch, is_deleted=False)
        )
    except MealClaim.DoesNotExist:
        raise Http404("meal claim not found")

    _annotate_claim_participants([claim])
    return _render_meal_row(request, claim)


@login_required(login_url="common:login")
def meals_edit_row(request, claim_id: int):
    branch = _get_branch_or_404(request)
    try:
        claim = (
            MealClaim.objects
            .select_related("user")
            .prefetch_related("participants__user")
            .get(id=claim_id, branch=branch, is_deleted=False)
        )
    except MealClaim.DoesNotExist:
        raise Http404("meal claim not found")

    _annotate_claim_participants([claim])
    return _render_meal_row_edit(request, claim, _get_branch_users(branch, claim.used_date))


@login_required(login_url="common:login")
def meals_update(request, claim_id: int):
    branch = _get_branch_or_404(request)
    used_date_str = request.POST.get("used_date")
    amount_str = request.POST.get("amount")
    merchant_name = (request.POST.get("merchant_name") or "").strip()

    if not used_date_str or not amount_str:
        return HttpResponse("사용일과 총액은 필수입니다.", status=400)
    if not merchant_name:
        return HttpResponse("가맹점명은 필수입니다.", status=400)

    try:
        used_date = datetime.strptime(used_date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponse("사용일은 YYYY-MM-DD 형식이어야 합니다.", status=400)

    amount, error = _parse_amount(amount_str, "총액")
    if error:
        return HttpResponse(error, status=400)

    approval_no, err = _parse_approval_no(
        request.POST.get("approval_no"),
        branch=branch,
        used_date=used_date,
        exclude_claim_id=claim_id,  # 수정에서는 자기 자신 제외
    )
    if err:
        return HttpResponse(err, status=400)

    participants, participant_errors = _parse_participants(request.POST, branch, used_date)
    if participant_errors:
        return HttpResponse("\n".join(participant_errors), status=400)

    # Server-side validation ensures participant sum matches total amount.
    if sum(p[1] for p in participants) != amount:
        return HttpResponse("분배 합계가 총액과 일치해야 합니다.", status=400)

    ym = used_date.strftime("%Y%m")
    if _is_month_closed(branch, ym):
        return HttpResponse("마감된 월은 수정할 수 없습니다.", status=403)

    with transaction.atomic():
        try:
            claim = (
                MealClaim.objects
                .select_for_update()
                .select_related("user")
                .prefetch_related("participants__user")
                .get(id=claim_id, branch=branch, is_deleted=False)
            )
        except MealClaim.DoesNotExist:
            raise Http404("meal claim not found")

        claim.used_date = used_date
        claim.amount = amount
        claim.approval_no = approval_no
        claim.merchant_name = merchant_name
        claim.save()
        MealClaimParticipant.objects.filter(claim=claim).delete()
        MealClaimParticipant.objects.bulk_create([
            MealClaimParticipant(claim=claim, user_id=user_id, amount=amount_value)
            for user_id, amount_value in participants
        ])

    claim = (
        MealClaim.objects
        .select_related("user")
        .prefetch_related("participants__user")
        .get(id=claim.id)
    )
    _annotate_claim_participants([claim])

    resp = _render_meal_row(request, claim)
    resp["HX-Trigger"] = json.dumps({"toast": {"message": "수정되었습니다.", "level": "success"}})
    return resp


# 엑셀에서 비로그인으로 가져갈 수 있도록 JSON 형태로 내려줌 -> 향후 제거 예정
def work_meal_json(request, stand_ym: str | None = None):
    stand_ym = stand_ym or request.GET.get("stand_ym") or timezone.now().strftime("%Y%m")

    branch = getattr(request, "branch", None)
    if branch is None:
        raise Http404("branch code is required")

    # dept/position 등 포함된 rows를 만들어 주는 함수
    stand_ym, rows = build_meal_status_rows(stand_ym, branch=branch)

    # 요청 형태로 단순화: [{"emp_name": "...", "total_amount": 123}, ...]
    simple_rows = []
    for r in rows:
        simple_rows.append({
            "emp_name": r.get("emp_name"),
            "total_amount": r.get("total_amount") or 0,
        })

    resp = JsonResponse(simple_rows, safe=False, json_dumps_params={"ensure_ascii": False})

    # 필요 시 파일 다운로드 형태
    if request.GET.get("download") == "1":
        resp["Content-Disposition"] = f'attachment; filename="work_meal_json_{stand_ym}.json"'
    return resp
