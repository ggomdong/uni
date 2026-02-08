from calendar import monthrange
from datetime import datetime, date
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from wtm.models import Schedule, MealClaim, BranchMonthClose  # Schedule에 d1~d31 FK가 있다고 가정
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
            "dept": u["dept"],
            "position": u["position"],
            "emp_name": u["emp_name"],
            "total_amount": total if total > 0 else None,  # 0이면 '-'로 보이게
            "used_amount": None,
            "balance": None,
        })

    return stand_ym, rows


@login_required(login_url="common:login")
def work_meal_status(request, stand_ym: str | None = None):
    branch = getattr(request, "branch", None)
    if branch is None:
        raise Http404("branch code is required")

    stand_ym, rows = build_meal_status_rows(stand_ym, branch=branch)

    return render(request, "wtm/work_meal_status.html", {
        "stand_ym": stand_ym,
        "rows": rows,
        "active_metric": "meal",  # 메뉴 하이라이트/탭 구분용(선택)
    })


def _get_branch_or_404(request):
    branch = getattr(request, "branch", None) or getattr(request.user, "branch", None)
    if branch is None:
        raise Http404("branch code is required")
    return branch


def _resolve_ym(ym: str | None):
    if not ym or len(ym) != 6 or not ym.isdigit():
        return timezone.now().strftime("%Y%m")
    return ym


def _month_range(ym: str):
    year = int(ym[:4])
    month = int(ym[4:6])
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _is_month_closed(branch, ym: str):
    return BranchMonthClose.objects.filter(branch=branch, ym=ym, is_closed=True).exists()


def _render_meal_table(request, branch, ym: str):
    start_date, end_date = _month_range(ym)
    claims = (
        MealClaim.objects
        .select_related("user")
        .filter(branch=branch, is_deleted=False, used_date__gte=start_date, used_date__lte=end_date)
        .order_by("used_date", "id")
    )
    is_closed = _is_month_closed(branch, ym)
    return render(request, "tw/wtm/_work_meals_table.html", {
        "ym": ym,
        "claims": claims,
        "is_closed": is_closed,
    })


@login_required(login_url="common:login")
def meals_index(request):
    branch = _get_branch_or_404(request)
    ym = _resolve_ym(request.GET.get("ym"))

    if request.headers.get("HX-Request") == "true":
        return _render_meal_table(request, branch, ym)

    start_date, end_date = _month_range(ym)
    claims = (
        MealClaim.objects
        .select_related("user")
        .filter(branch=branch, is_deleted=False, used_date__gte=start_date, used_date__lte=end_date)
        .order_by("used_date", "id")
    )
    is_closed = _is_month_closed(branch, ym)
    return render(request, "tw/wtm/work_meal.html", {
        "ym": ym,
        "claims": claims,
        "is_closed": is_closed,
    })


@login_required(login_url="common:login")
def meals_new(request):
    branch = _get_branch_or_404(request)
    used_date_str = request.POST.get("used_date")
    amount_str = request.POST.get("amount")
    memo = request.POST.get("memo") or None

    if not used_date_str or not amount_str:
        return HttpResponse("used_date와 amount는 필수입니다.", status=400)

    try:
        used_date = datetime.strptime(used_date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponse("used_date는 YYYY-MM-DD 형식이어야 합니다.", status=400)

    try:
        amount = int(amount_str)
    except ValueError:
        return HttpResponse("amount는 숫자여야 합니다.", status=400)

    ym = used_date.strftime("%Y%m")
    if _is_month_closed(branch, ym):
        return HttpResponse("마감된 월은 등록할 수 없습니다.", status=403)

    MealClaim.objects.create(
        branch=branch,
        user=request.user,
        used_date=used_date,
        amount=amount,
        memo=memo,
    )

    return _render_meal_table(request, branch, ym)


@login_required(login_url="common:login")
def meals_delete(request, claim_id: int):
    branch = _get_branch_or_404(request)
    try:
        claim = MealClaim.objects.get(id=claim_id, branch=branch, is_deleted=False)
    except MealClaim.DoesNotExist:
        raise Http404("meal claim not found")

    if claim.user_id != request.user.id:
        return HttpResponse("본인 항목만 삭제할 수 있습니다.", status=403)

    ym = claim.used_date.strftime("%Y%m")
    if _is_month_closed(branch, ym):
        return HttpResponse("마감된 월은 삭제할 수 없습니다.", status=403)

    claim.is_deleted = True
    claim.save()

    return _render_meal_table(request, branch, ym)


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
