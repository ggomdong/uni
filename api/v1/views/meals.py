from datetime import date

from django.db.models import Sum, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from wtm.models import MealClaim, MealClaimParticipant
from wtm.services import branch_access as ba
from wtm.services import date_utils as du
from wtm.services import meal_claims as svc

from .common import (
    ensure_active_employee_or_403,
    get_branch_or_error,
    validation_error,
    forbidden_response,
    not_found_response,
)


class MealMySummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = get_branch_or_error(request)
        if error_resp:
            return error_resp

        ym, error = du.normalize_ym(request.query_params.get("ym"))
        if error:
            return validation_error(error)

        start_date, end_date = du.month_range(ym)
        total_amount = svc.calculate_user_meal_total(request.user, branch, ym)

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
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = get_branch_or_error(request)
        if error_resp:
            return error_resp

        ym, error = du.normalize_ym(request.query_params.get("ym"))
        if error:
            return validation_error(error)

        start_date, end_date = du.month_range(ym)
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
            my_amount, participant_sum, participants_count = svc.claim_participants_summary_for_user(
                claim,
                request.user.id,
            )
            can_edit = claim.user_id == request.user.id
            items.append({
                "id": claim.id,
                "used_date": claim.used_date.strftime("%Y-%m-%d"),
                "merchant_name": claim.merchant_name,
                "approval_no": claim.approval_no,
                "total_amount": claim.amount,
                "my_amount": my_amount,
                "participants_count": participants_count,
                "participant_sum": participant_sum,
                "created_by": {"id": claim.user_id, "emp_name": claim.user.emp_name},
                "can_edit": can_edit,
                "can_delete": can_edit,
            })

        return Response({"ym": ym, "items": items})


class MealOptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = get_branch_or_error(request)
        if error_resp:
            return error_resp

        used_date_str = request.query_params.get("used_date")
        if used_date_str:
            used_date, error = du.parse_used_date(used_date_str)
            if error:
                return validation_error(error)
            ym = used_date.strftime("%Y%m")
        else:
            ym, error = du.normalize_ym(request.query_params.get("ym"))
            if error:
                return validation_error(error)
            used_date = date(int(ym[:4]), int(ym[4:6]), 1)

        users_qs = ba.get_branch_users(branch, used_date)
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
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = get_branch_or_error(request)
        if error_resp:
            return error_resp

        payload, errors = svc.parse_claim_payload(request.data, branch)
        if errors:
            return validation_error(errors[0], details=errors)

        try:
            claim = svc.create_claim(request.user, branch, payload)
        except ValueError as e:
            return forbidden_response(str(e))
        claim = (
            MealClaim.objects
            .select_related("user")
            .prefetch_related("participants__user")
            .get(id=claim.id)
        )
        return Response(svc.serialize_claim_detail(claim, request.user), status=status.HTTP_201_CREATED)


class MealClaimDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id: int):
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = get_branch_or_error(request)
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
            return not_found_response("meal claim not found")

        if not claim.participants.filter(user=request.user).exists():
            return not_found_response("meal claim not found")

        return Response(svc.serialize_claim_detail(claim, request.user))

    def patch(self, request, claim_id: int):
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = get_branch_or_error(request)
        if error_resp:
            return error_resp

        try:
            claim = MealClaim.objects.get(id=claim_id, branch=branch, is_deleted=False)
        except MealClaim.DoesNotExist:
            return not_found_response("meal claim not found")

        if claim.user_id != request.user.id:
            return forbidden_response()

        payload, errors = svc.parse_claim_payload(
            request.data,
            branch,
            exclude_claim_id=claim.id,
        )
        if errors:
            return validation_error(errors[0], details=errors)

        try:
            claim = svc.update_claim(branch, claim.id, payload)
        except ValueError as e:
            return forbidden_response(str(e))
        except MealClaim.DoesNotExist:
            return not_found_response("meal claim not found")

        claim = (
            MealClaim.objects
            .select_related("user")
            .prefetch_related("participants__user")
            .get(id=claim.id)
        )
        return Response(svc.serialize_claim_detail(claim, request.user))

    def delete(self, request, claim_id: int):
        resp = ensure_active_employee_or_403(request.user)
        if resp is not None:
            return resp

        branch, error_resp = get_branch_or_error(request)
        if error_resp:
            return error_resp

        try:
            claim = MealClaim.objects.get(id=claim_id, branch=branch, is_deleted=False)
        except MealClaim.DoesNotExist:
            return not_found_response("meal claim not found")

        if claim.user_id != request.user.id:
            return forbidden_response()

        try:
            svc.soft_delete_claim(branch, claim.id)
        except ValueError as e:
            return forbidden_response(str(e))
        except MealClaim.DoesNotExist:
            return not_found_response("meal claim not found")

        return Response({"ok": True})
