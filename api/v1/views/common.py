from __future__ import annotations

from datetime import datetime, date
from typing import Any

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from wtm.services import date_utils as du


def validation_error(message: str, *, code: str = "validation_error", details: Any | None = None) -> Response:
    payload: dict[str, Any] = {"error": code, "message": message}
    if details is not None:
        payload["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


def forbidden_response(message: str = "권한이 없습니다.", *, code: str = "forbidden") -> Response:
    return Response({"error": code, "message": message}, status=status.HTTP_403_FORBIDDEN)


def not_found_response(message: str = "대상을 찾을 수 없습니다.", *, code: str = "not_found") -> Response:
    return Response({"error": code, "message": message}, status=status.HTTP_404_NOT_FOUND)


def get_branch_or_error(request):
    # middleware(request.branch) 우선, 없으면 user.branch
    branch = getattr(request, "branch", None) or getattr(request.user, "branch", None)
    if branch is None:
        return None, validation_error("branch code is required", code="branch_required")
    return branch, None


def ensure_active_employee_or_403(user):
    # NOTE: localtime/localdate 이슈가 있었다고 해서 timezone.now().date()로만 처리
    today = timezone.now().date()
    out_date = getattr(user, "out_date", None)
    if out_date and out_date < today:
        return Response({"error": "out_user", "message": "퇴사자는 사용할 수 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    return None


def parse_ym(value: str | None, *, default_to_now: bool = True) -> tuple[str | None, Response | None]:
    """
    'YYYYMM' 또는 'YYYY-MM' 입력을 'YYYYMM'으로 정규화
    """
    if not value:
        if default_to_now:
            return timezone.now().strftime("%Y%m"), None
        return None, validation_error("ym is required", code="ym_required")

    ym = du.resolve_month_input(value)
    if ym is not None:
        return ym, None
    return None, validation_error("ym은 YYYYMM 또는 YYYY-MM 형식이어야 합니다.", details={"value": value})


def month_range(ym: str) -> tuple[date, date]:
    return du.month_range(ym)


def parse_date_yyyy_mm_dd(value: str | None, *, field_name: str = "date") -> tuple[date | None, Response | None]:
    if not value:
        return None, validation_error(f"{field_name} is required", code=f"{field_name}_required")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except ValueError:
        return None, validation_error(f"{field_name}는 YYYY-MM-DD 형식이어야 합니다.", details={"value": value})
