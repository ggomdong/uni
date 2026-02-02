from calendar import monthrange
from django.utils import timezone
from django.http import JsonResponse, Http404

from django.contrib.auth.decorators import login_required

from wtm.models import Module, Schedule
from .helpers import fetch_base_users_for_month


def build_vacation_rows(year: int, *, branch, is_contract_checked: bool = False) -> list[dict]:
    """
    특정 연도에 대해, 스케줄에 module.name='연차'가 들어간 (직원명, 날짜) 리스트를 생성.
    반환: [{"emp_name": "...", "date": "YYYY-MM-DD"}, ...]
    """

    vacation_module_ids = set(
        Module.objects.filter(branch=branch, name__iexact="연차")
        .values_list("id", flat=True)
    )
    if not vacation_module_ids:
        return []

    rows: list[dict] = []

    for month in range(1, 13):
        stand_ym = f"{year:04d}{month:02d}"

        base_users = fetch_base_users_for_month(
            stand_ym, branch=branch, is_contract_checked=is_contract_checked
        )
        if not base_users:
            continue

        uid_list = [u["user_id"] for u in base_users]
        last_day_num = monthrange(year, month)[1]

        # FK id만 읽어와서 비교(성능)
        only_fields = ["user_id", "year", "month"] + [f"d{i}_id" for i in range(1, 32)]
        schedules = (
            Schedule.objects
            .filter(user_id__in=uid_list, year=str(year), month=f"{month:02d}", branch=branch)
            .only(*only_fields)
        )
        schedule_map = {s.user_id: s for s in schedules}

        # base_users 순서(부서/직위/입사일)를 그대로 보장
        for u in base_users:
            sch = schedule_map.get(u["user_id"])
            if not sch:
                continue

            emp_name = u.get("emp_name") or ""

            for d in range(1, last_day_num + 1):
                mid = getattr(sch, f"d{d}_id", None)
                if mid in vacation_module_ids:
                    rows.append({
                        "emp_name": emp_name,
                        "date": f"{year:04d}-{month:02d}-{d:02d}",
                    })

    return rows


# 엑셀에서 비로그인으로 가져갈 수 있도록 JSON 형태로 내려줌
def work_vacation_json(request, year: str | None = None):
    year = year or request.GET.get("year")

    if not year:
        year = timezone.now().strftime("%Y")

    try:
        y = int(year)
        if y < 2000 or y > 9999:
            raise ValueError
    except ValueError:
        return JsonResponse(
            {"error": "year는 YYYY 형식의 유효한 숫자여야 합니다."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    branch = getattr(request, "branch", None)
    if branch is None:
        raise Http404("branch code is required")

    # 필요하면 계약확인 대상만 뽑고 싶을 때 옵션화 가능
    # is_contract_checked = request.GET.get("contract_checked") == "1"
    is_contract_checked = False

    rows = build_vacation_rows(y, branch=branch, is_contract_checked=is_contract_checked)

    resp = JsonResponse(rows, safe=False, json_dumps_params={"ensure_ascii": False})

    if request.GET.get("download") == "1":
        resp["Content-Disposition"] = f'attachment; filename="work_vacation_{y}.json"'
    return resp
