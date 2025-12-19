from calendar import monthrange
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from wtm.models import Schedule  # Schedule에 d1~d31 FK가 있다고 가정
from .helpers import sec_to_hhmmss, fetch_base_users_for_month


def build_meal_status_rows(stand_ym: str | None):
    stand_ym = stand_ym or timezone.now().strftime("%Y%m")
    year, month = int(stand_ym[:4]), int(stand_ym[4:6])
    last_day_num = monthrange(year, month)[1]

    # 1) 대상자 : 전 직원
    base_users = fetch_base_users_for_month(stand_ym, is_contract_checked=False)
    if not base_users:
        return stand_ym, []

    uid_list = [u["user_id"] for u in base_users]

    # 2) 스케줄을 한 번에 조회 (d1~d31 모듈까지 select_related)
    rel_fields = [f"d{i}" for i in range(1, 32)]
    schedules = (
        Schedule.objects
        .select_related(*rel_fields)
        .filter(user_id__in=uid_list, year=str(year), month=f"{month:02d}")
    )
    schedule_map = {s.user_id: s for s in schedules}

    # 3) rows 구성
    rows = []
    for u in base_users:
        sch = schedule_map.get(u["user_id"])
        total = 0

        if sch:
            for d in range(1, last_day_num + 1):
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
    stand_ym, rows = build_meal_status_rows(stand_ym)

    return render(request, "wtm/work_meal_status.html", {
        "stand_ym": stand_ym,
        "rows": rows,
        "active_metric": "meal",  # 메뉴 하이라이트/탭 구분용(선택)
    })
