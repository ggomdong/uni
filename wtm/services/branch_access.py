from __future__ import annotations

from datetime import date

from django.db.models import Q

from common.models import User
from wtm.models import BranchMonthClose


def get_branch_users(branch, used_date: date | None):
    base_qs = User.objects.filter(branch=branch, is_active=True, is_employee=True)
    if used_date:
        base_qs = base_qs.filter(join_date__lte=used_date).filter(
            Q(out_date__isnull=True) | Q(out_date__gte=used_date)
        )
    return base_qs.order_by("emp_name")


def is_month_closed(branch, ym: str) -> bool:
    return BranchMonthClose.objects.filter(branch=branch, ym=ym, is_closed=True).exists()
