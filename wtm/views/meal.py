import json
import logging
from datetime import date
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render

from common.models import User
from wtm.models import MealClaim
from wtm.services import branch_access as ba
from wtm.services import date_utils as du
from wtm.services import meal_claims as svc
from wtm.services import meal_queries as q

logger = logging.getLogger(__name__)


@login_required(login_url="common:login")
def work_meal_status(request, stand_ym: str | None = None):
    branch = getattr(request, "branch", None)
    if branch is None:
        raise Http404("branch code is required")

    requested_ym = du.resolve_month_input(request.GET.get("month")) or request.GET.get("ym") or stand_ym
    stand_ym = du.normalize_ym_or_now(requested_ym)
    stand_ym, rows = q.build_meal_status_rows(stand_ym, branch=branch)
    usage_map = q.build_meal_usage_summary_map(stand_ym, branch=branch)
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
        "nav": {
            "mode": "month",
            "value": f"{stand_ym[:4]}-{stand_ym[4:]}",
            "url_template": ".?month={value}",
            "hx_target": "#status-table",
            "hx_swap": "outerHTML",
            "hx_push_url": "true",
            "hx_indicator": "#status-month-indicator",
        },
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "tw/wtm/meal/_work_meal_status_table.html", context)

    return render(request, "tw/wtm/work_meal_status.html", context)


@login_required(login_url="common:login")
def work_meal_status_user_modal(request, user_id: int):
    branch = _get_branch_or_404(request)
    requested_ym = du.resolve_month_input(request.GET.get("month")) or request.GET.get("ym")
    stand_ym = du.normalize_ym_or_now(requested_ym)
    try:
        target_user, participants, total_personal, total_claim_amount = q.get_user_month_participants(
            user_id, branch=branch, ym=stand_ym
        )
    except User.DoesNotExist:
        raise Http404("user not found")
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


def _render_meal_table(request, branch, ym: str):
    claims, is_closed = q.list_month_claims_for_table(branch=branch, ym=ym)
    q.hydrate_claim_participants(claims)
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


@login_required(login_url="common:login")
def meals_index(request):
    branch = _get_branch_or_404(request)
    ym = du.resolve_month_input(request.GET.get("month")) or du.normalize_ym_or_now(request.GET.get("ym"))

    if request.headers.get("HX-Request") == "true":
        return _render_meal_table(request, branch, ym)

    claims, is_closed = q.list_month_claims_for_table(branch=branch, ym=ym)
    q.hydrate_claim_participants(claims)
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
        "users": ba.get_branch_users(branch, default_used_date),
        "nav": {
            "mode": "month",
            "value": f"{ym[:4]}-{ym[4:]}",
            "url_template": ".?month={value}",
            "hx_target": "#meal-table",
            "hx_swap": "outerHTML",
            "hx_push_url": "true",
            "hx_indicator": "#meal-month-indicator",
        },
    })


@login_required(login_url="common:login")
def meals_new(request):
    branch = _get_branch_or_404(request)
    payload, errors = svc.parse_claim_payload_form(request.POST, branch)
    if errors:
        return HttpResponse("\n".join(errors), status=400)

    try:
        claim = svc.create_claim(request.user, branch, payload)
    except ValueError as e:
        return HttpResponse(str(e), status=403)
    logger.info(
        "meal claim created via web: actor_id=%s claim_id=%s branch_id=%s",
        request.user.id, claim.id, branch.id,
    )

    # HTMX swaps the table outerHTML after create/delete.
    ym = payload["used_date"].strftime("%Y%m")
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

    try:
        ym = svc.soft_delete_claim(branch, claim.id)
    except ValueError as e:
        return HttpResponse(str(e), status=403)
    logger.info(
        "meal claim deleted via web: actor_id=%s claim_id=%s branch_id=%s",
        request.user.id, claim.id, branch.id,
    )

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

    q.hydrate_claim_participants([claim])
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

    q.hydrate_claim_participants([claim])
    return _render_meal_row_edit(request, claim, ba.get_branch_users(branch, claim.used_date))


@login_required(login_url="common:login")
def meals_update(request, claim_id: int):
    branch = _get_branch_or_404(request)
    payload, errors = svc.parse_claim_payload_form(
        request.POST,
        branch,
        exclude_claim_id=claim_id,
    )
    if errors:
        return HttpResponse("\n".join(errors), status=400)

    try:
        claim = svc.update_claim(branch, claim_id, payload)
    except ValueError as e:
        return HttpResponse(str(e), status=403)
    except MealClaim.DoesNotExist:
        raise Http404("meal claim not found")
    logger.info(
        "meal claim updated via web: actor_id=%s claim_id=%s branch_id=%s",
        request.user.id, claim.id, branch.id,
    )

    claim = (
        MealClaim.objects
        .select_related("user")
        .prefetch_related("participants__user")
        .get(id=claim.id)
    )
    q.hydrate_claim_participants([claim])

    resp = _render_meal_row(request, claim)
    resp["HX-Trigger"] = json.dumps({"toast": {"message": "수정되었습니다.", "level": "success"}})
    return resp


# 엑셀에서 비로그인으로 가져갈 수 있도록 JSON 형태로 내려줌 -> 향후 제거 예정
def work_meal_json(request, stand_ym: str | None = None):
    stand_ym = du.normalize_ym_or_now(stand_ym or request.GET.get("stand_ym"))

    branch = getattr(request, "branch", None)
    if branch is None:
        raise Http404("branch code is required")

    # dept/position 등 포함된 rows를 만들어 주는 함수
    stand_ym, rows = q.build_meal_status_rows(stand_ym, branch=branch)

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
