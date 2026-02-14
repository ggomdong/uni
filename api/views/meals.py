from calendar import monthrange
from datetime import datetime, date

from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from wtm.models import Schedule, MealClaim, MealClaimParticipant
from wtm.views.helpers import fetch_base_users_for_month
from wtm.services.meal_claims import (
    _resolve_month_input,
    _month_range,
    _get_branch_users,
    _parse_amount,
    _parse_approval_no,
    parse_participants_json,
)

from .common import (
    ensure_active_employee_or_403,
    _get_branch_or_error,
    _validation_error,
    _forbidden_response,
    _not_found_response,
    parse_ym,
)


def _normalize_ym(ym_value):
    if not ym_value:
        return timezone.now().strftime("%Y%m"), None
    normalized = _resolve_month_input(ym_value)
    if normalized is None:
        return None, _validation_error("ym은 YYYY-MM 또는 YYYYMM 형식이어야 합니다.")
    return normalized, None


def _parse_used_date(value):
    if not value:
        return None, "사용일은 필수입니다."
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except ValueError:
        return None, "사용일은 YYYY-MM-DD 형식이어야 합니다."


def _calculate_user_meal_total(user, branch, ym):
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


def _parse_claim_payload(data, branch, *, exclude_claim_id=None):
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

    used_date, error = _parse_used_date(used_date_str)
    if error:
        errors.append(error)
        return None, errors

    amount, error = _parse_amount(amount_raw, "총액")
    if error:
        errors.append(error)
        return None, errors

    approval_no, error = _parse_approval_no(
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


def _serialize_claim_detail(claim, request_user):
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


class MealMySummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        ym, error_resp = _normalize_ym(request.query_params.get("ym"))
        if error_resp:
            return error_resp

        start_date, end_date = _month_range(ym)
        total_amount = _calculate_user_meal_total(request.user, branch, ym)

        summary = (
            MealClaimParticipant.objects
            .filter(
                user=request.user,
                claim__branch=branch,
                claim__is_deleted=False,
                claim__used_date__range=(start_date, end_date),
            )
            .aggregate(
                used_amount=Sum("amount"),
                claim_count=Count("claim_id", distinct=True),
            )
        )
        used_amount = summary.get("used_amount") or 0
        claim_count = summary.get("claim_count") or 0

        return Response({
            "ym": ym,
            "total_amount": total_amount,
            "used_amount": used_amount,
            "balance": total_amount - used_amount,
            "claim_count": claim_count,
        })


class MealMyItemsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        ym, error = _normalize_ym(request.query_params.get("ym"))
        if error:
            return _validation_error(error)

        start_date, end_date = _month_range(ym)
        claims = (
            MealClaim.objects
            .select_related("user")
            .prefetch_related("participants__user")
            .filter(
                branch=branch,
                is_deleted=False,
                used_date__range=(start_date, end_date),
                participants__user=request.user,
            )
            .distinct()
            .order_by("used_date", "id")
        )

        items = []
        for claim in claims:
            participants = list(claim.participants.all())
            participant_sum = sum(p.amount for p in participants)
            my_amount = next((p.amount for p in participants if p.user_id == request.user.id), 0)
            can_edit = claim.user_id == request.user.id
            items.append({
                "id": claim.id,
                "used_date": claim.used_date.strftime("%Y-%m-%d"),
                "merchant_name": claim.merchant_name,
                "approval_no": claim.approval_no,
                "total_amount": claim.amount,
                "my_amount": my_amount,
                "participants_count": len(participants),
                "participant_sum": participant_sum,
                "created_by": {"id": claim.user_id, "emp_name": claim.user.emp_name},
                "can_edit": can_edit,
                "can_delete": can_edit,
            })

        return Response({"ym": ym, "items": items})


class MealOptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        used_date_str = request.query_params.get("used_date")
        if used_date_str:
            used_date, error = _parse_used_date(used_date_str)
            if error:
                return _validation_error(error)
            ym = used_date.strftime("%Y%m")
        else:
            ym, error = _normalize_ym(request.query_params.get("ym"))
            if error:
                return _validation_error(error)
            used_date = date(int(ym[:4]), int(ym[4:6]), 1)

        users_qs = _get_branch_users(branch, used_date)
        users = [
            {
                "id": u.id,
                "emp_name": u.emp_name,
                "dept": u.dept or "",
                "position": u.position or "",
            }
            for u in users_qs
        ]

        groups_map = {}
        for u in users:
            dept = u["dept"] or ""
            groups_map.setdefault(dept, []).append({
                "id": u["id"],
                "emp_name": u["emp_name"],
                "position": u["position"],
            })

        groups = [
            {"dept": dept, "members": members}
            for dept, members in groups_map.items()
        ]

        return Response({
            "ym": ym,
            "users": users,
            "groups": groups,
        })


class MealClaimCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        payload, errors = _parse_claim_payload(request.data, branch)
        if errors:
            return _validation_error(errors[0], details=errors)

        with transaction.atomic():
            claim = MealClaim.objects.create(
                branch=branch,
                user=request.user,
                used_date=payload["used_date"],
                amount=payload["amount"],
                approval_no=payload["approval_no"],
                merchant_name=payload["merchant_name"],
            )
            MealClaimParticipant.objects.bulk_create([
                MealClaimParticipant(claim=claim, user_id=user_id, amount=amount_value)
                for user_id, amount_value in payload["participants"]
            ])

        claim = (
            MealClaim.objects
            .select_related("user")
            .prefetch_related("participants__user")
            .get(id=claim.id)
        )
        return Response(_serialize_claim_detail(claim, request.user), status=status.HTTP_201_CREATED)


class MealClaimDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id: int):
        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        try:
            claim = (
                MealClaim.objects
                .select_related("user")
                .prefetch_related("participants__user")
                .get(id=claim_id, branch=branch, is_deleted=False)
            )
        except MealClaim.DoesNotExist:
            return _not_found_response("meal claim not found")

        if not claim.participants.filter(user=request.user).exists():
            return _not_found_response("meal claim not found")

        return Response(_serialize_claim_detail(claim, request.user))

    def patch(self, request, claim_id: int):
        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        try:
            claim = MealClaim.objects.get(id=claim_id, branch=branch, is_deleted=False)
        except MealClaim.DoesNotExist:
            return _not_found_response("meal claim not found")

        if claim.user_id != request.user.id:
            return _forbidden_response()

        payload, errors = _parse_claim_payload(
            request.data,
            branch,
            exclude_claim_id=claim.id,
        )
        if errors:
            return _validation_error(errors[0], details=errors)

        with transaction.atomic():
            claim = MealClaim.objects.select_for_update().get(id=claim.id, branch=branch, is_deleted=False)
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

        claim = (
            MealClaim.objects
            .select_related("user")
            .prefetch_related("participants__user")
            .get(id=claim.id)
        )
        return Response(_serialize_claim_detail(claim, request.user))

    def delete(self, request, claim_id: int):
        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        try:
            claim = MealClaim.objects.get(id=claim_id, branch=branch, is_deleted=False)
        except MealClaim.DoesNotExist:
            return _not_found_response("meal claim not found")

        if claim.user_id != request.user.id:
            return _forbidden_response()

        claim.is_deleted = True
        claim.save()
        return Response({"ok": True})
