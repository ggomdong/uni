from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from calendar import monthrange
from datetime import datetime, date
from .serializers import UserProfileSerializer, AttendanceSerializer, MonthlyAttendanceDaySerializer, WorkSerializer, BeaconSerializer
from common.models import User, Holiday, Business
from wtm.models import Work, Schedule, Beacon, MealClaim, MealClaimParticipant
from wtm.services.attendance import build_monthly_attendance_for_user
from wtm.views.helpers import fetch_base_users_for_month
from wtm.views.meal import (
    _resolve_month_input,
    _month_range,
    _get_branch_users,
    _parse_amount,
    _parse_approval_no,
    parse_participants_json,
)

_TEST_MODE = False
_TEST_TODAY = datetime(2025, 12, 5).date()
_TEST_NOW = datetime.combine(_TEST_TODAY, datetime.strptime("08:35", "%H:%M").time())


def ensure_active_employee_or_403(user):
    """
    퇴사자면 403 Response를 반환하고,
    재직자면 None을 반환한다.
    """
    today = timezone.now().date()
    if getattr(user, "out_date", None) and user.out_date < today:
        return Response(
            {"error": "out_user", "message": "퇴사자는 사용할 수 없습니다."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _validation_error(message, details=None):
    payload = {"error": "validation_error", "message": message}
    if details:
        payload["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


def _forbidden_response():
    return Response(
        {"error": "forbidden", "message": "권한이 없습니다."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _not_found_response(message):
    return Response(
        {"error": "not_found", "message": message},
        status=status.HTTP_404_NOT_FOUND,
    )


def _get_branch_or_error(request):
    branch = getattr(request, "branch", None) or getattr(request.user, "branch", None)
    if branch is None:
        return None, _not_found_response("branch not found")
    return branch, None


def _normalize_ym(ym_value):
    if not ym_value:
        return timezone.now().strftime("%Y%m"), None
    normalized = _resolve_month_input(ym_value)
    if normalized is None:
        return None, "ym은 YYYY-MM 또는 YYYYMM 형식이어야 합니다."
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


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get('username')
        device_id = self.context['request'].data.get('device_id')

        if not device_id:
            raise ValidationError("기기 식별값이 누락되었습니다.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthenticationFailed("아이디 혹은 비밀번호가 올바르지 않습니다.")

        # 인증 먼저
        data = super().validate(attrs)

        # 디바이스 검증/등록은 로그인 성공 이후에만 수행
        if user.device_id:
            if user.is_employee and user.device_id != device_id:
                raise ValidationError("등록되지 않은 기기입니다. 관리자에게 문의하세요.")
        else:
            user.device_id = device_id
            user.save()

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        today = timezone.now().date()

        # 퇴사자 조건에 해당되면 로그인 차단
        is_out = User.objects.filter(
            username=username,
            out_date__isnull=False,
            out_date__lt=today
        ).exists()

        if is_out:
            return Response(
                {"error": "out_user", "message": "퇴사자는 로그인할 수 없습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            response = super().post(request, *args, **kwargs)
            return response
        except AuthenticationFailed as e:
            return Response(
                {"error": "invalid_credentials", "message": "아이디 혹은 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except InvalidToken as e:
            return Response(
                {"error": "token_expired", "message": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except ValidationError as e:
            detail = e.detail

            if isinstance(detail, list):
                # ex) 기기 식별값이 누락되었습니다.
                message = detail[0]
            elif isinstance(detail, dict):
                # ex) {'non_field_errors': ['...']}
                non_field = detail.get('non_field_errors')
                if isinstance(non_field, list) and non_field:
                    message = non_field[0]
                else:
                    message = str(detail)
            else:
                message = str(detail)

            return Response(
                {"error": "validation_error", "message": str(message)},
                status=status.HTTP_403_FORBIDDEN,
            )

        except Exception as e:
            return Response(
                {"error": "unknown", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AttendanceAPIView(APIView):
    """
    앱 사용자 1명의 오늘의 근무표, 출퇴근 정보
    GET /api/attendance

    - 앱의 홈화면에서 사용자의 정보를 가져올때 사용
    - 인증된 사용자(request.user)의 근무표, 출퇴근 정보, 조퇴/연장근로 판단
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(user)
        if resp is not None:
            return resp

        TEST_MODE = _TEST_MODE

        if TEST_MODE:
            today = _TEST_TODAY
            now = _TEST_NOW
        else:
            now = timezone.now()
            today = now.date()

        # 출근/퇴근 기록 조회
        checkin = (
            Work.objects.filter(user=user, branch=user.branch, work_code='I', record_day=today)
            .order_by('record_date')
            .first()
        )
        checkout = (
            Work.objects.filter(user=user, branch=user.branch, work_code='O', record_day=today)
            .order_by('-record_date')
            .first()
        )

        # 오늘 근무표 정보 조회
        try:
            schedule = Schedule.objects.get(
                user=user,
                branch=user.branch,
                year=str(today.year),
                month=f"{today.month:02}",
            )
            module = getattr(schedule, f"d{today.day}", None)
        except Schedule.DoesNotExist:
            module = None

        # 모듈 정보 및 시작/종료 시간 파싱. '-'이면 null로 처리
        module_cat = module.cat if module else None
        module_name = module.name if module else None
        work_start = module.start_time if module and module.start_time and module.start_time != '-' else None
        work_end = module.end_time if module and module.end_time and module.end_time != '-' else None

        # 현재 시간 기준 조퇴/연장근로 판단. True(조퇴), False(연장근로 후 퇴근)
        is_early_checkout = False

        if work_end and checkin:
            scheduled_end = datetime.combine(today, datetime.strptime(work_end, "%H:%M").time())
            if now < scheduled_end:
                is_early_checkout = True
            elif now > scheduled_end:
                is_early_checkout = False

        can_bypass_beacon = user.has_perm("wtm.bypass_beacon")

        data = {
            "emp_name": user.emp_name,
            "module_cat": module_cat,
            "module_name": module_name,
            "work_start": work_start,
            "work_end": work_end,
            "checkin_time": checkin.record_date if checkin else None,
            "checkout_time": checkout.record_date if checkout else None,
            "is_early_checkout": is_early_checkout,
            "can_bypass_beacon": can_bypass_beacon,
        }

        # print(data)

        serializer = AttendanceSerializer(data)
        return Response(serializer.data)


class MonthlyAttendanceAPIView(APIView):
    """
    앱 사용자 1명의 월간 근무표, 출퇴근 정보
    GET /api/attendance/monthly

    - 앱의 통계화면에서 사용자의 정보를 가져올때 사용
    - 인증된 사용자(request.user)의 월간 근무표, 출퇴근 정보, 지각/조퇴/연장근로/휴일근로 등 상태 값
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(user)
        if resp is not None:
            return resp

        now = timezone.now()

        try:
            year = int(request.query_params.get("year", now.year))
            month = int(request.query_params.get("month", now.month))
        except ValueError:
            return Response(
                {"error": "year, month는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        results = build_monthly_attendance_for_user(user, year, month)

        # print(results)

        serializer = MonthlyAttendanceDaySerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BeaconListAPIView(APIView):
    """
    내 지점 비콘 목록
    GET /api/beacons

    - 인증된 사용자(request.user)의 User.branch 기준으로 필터
    - is_active = True
    - valid_from / valid_to 기준으로 오늘 날짜에 유효한 것만
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now()

        # 1) 사용자에 branch가 설정되어 있는지 확인
        branch = getattr(user, "branch", None)
        if branch is None:
            return Response(
                {"detail": "사용자의 지점정보가 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) 해당 지점의 유효한 비콘만 조회
        results = Beacon.objects.filter(
            branch=branch,
            is_active=True,
        ).order_by("name")

        # print(results)

        serializer = BeaconSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user

        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(user)
        if resp is not None:
            return resp

        now = timezone.now()
        today = now.date()

        with transaction.atomic():
            # 오늘 출근 여부 확인
            checkin_exists = Work.objects.select_for_update().filter(
                user=user,
                branch=user.branch,
                work_code='I',
                record_day=today,
            ).exists()

            # 근태기록이 없으면 출근, 있으면 퇴근으로 설정
            work_code = 'I' if not checkin_exists else 'O'

            # Work 로그 저장
            serializer = WorkSerializer(data={
                'user': user.id,
                'work_code': work_code,
            })

            if serializer.is_valid():
                work = serializer.save(branch=user.branch)
                return Response({
                    "work": serializer.data,
                    "info": "출근하였습니다." if work_code == 'I' else "퇴근하였습니다."
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NonBusinessDayListAPIView(APIView):
    """
    특정 연월의 '영업하지 않는 날들' 목록을 내려주는 API.
    - Holiday(법정 공휴일)
    - Business(요일별 영업/비영업 패턴)을 모두 반영해서
      1) 날짜 단위 휴무일 리스트(non_business_days)
      2) 요일 단위 비영업 요일 리스트(non_business_weekdays)
    를 함께 내려준다.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        try:
            year = int(request.query_params.get("year", now.year))
            month = int(request.query_params.get("month", now.month))
        except ValueError:
            return Response({"detail": "year, month는 정수여야 합니다."}, status=400)
        if request.user.branch is None:
            return Response({"detail": "사용자의 지점정보가 없습니다."}, status=400)

        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # 1) Holiday 테이블 (법정 공휴일)
        holiday_qs = Holiday.objects.filter(
            branch=request.user.branch,
            holiday__range=(first_day, last_day),
        ).order_by("holiday")
        holiday_map = {h.holiday: h.holiday_name for h in holiday_qs}

        # 2) Business 테이블 (요일별 영업/비영업 패턴)
        business = (
            Business.objects.filter(branch=request.user.branch, stand_date__lte=last_day)
            .order_by("-stand_date")
            .first()
        )

        def is_business_open(d: date) -> bool:
            """
            해당 날짜 d가 영업일인지 판별.
            Business 없으면 '모든 요일 영업'으로 가정.
            mon~sun 필드는 'Y'=영업, 'N'=비영업
            """
            if business is None:
                return True

            weekday = d.weekday()  # 0=월, ..., 6=일
            code = {
                0: business.mon,
                1: business.tue,
                2: business.wed,
                3: business.thu,
                4: business.fri,
                5: business.sat,
                6: business.sun,
            }[weekday]

            return code == "Y"

        # 비영업 '요일' 리스트 (월=1, ..., 일=7 : Dart/TableCalendar 기준)
        non_business_weekdays: list[int] = []
        if business is not None:
            day_codes = [
                (business.mon, 1),  # 월
                (business.tue, 2),  # 화
                (business.wed, 3),  # 수
                (business.thu, 4),  # 목
                (business.fri, 5),  # 금
                (business.sat, 6),  # 토
                (business.sun, 7),  # 일
            ]
            # 여기서 'Y'가 아닌 요일만 비영업 요일로 추가
            for code, weekday in day_codes:
                if code != "Y":
                    non_business_weekdays.append(weekday)

        # days_meta = []
        non_business_days: list[str] = []

        for day in range(1, last_day.day + 1):
            d = date(year, month, day)
            is_holiday = d in holiday_map
            open_flag = is_business_open(d)

            # '영업하지 않는 날' = 공휴일 OR 비영업 요일
            is_non_business_day = is_holiday or (not open_flag)

            if is_non_business_day:
                non_business_days.append(d.strftime("%Y-%m-%d"))

            # days_meta.append(
            #     {
            #         "date": date_str,
            #         "is_holiday": is_holiday,
            #         "holiday_name": holiday_map.get(d),
            #         "is_business_open": open_flag,
            #         "is_non_business_day": is_non_business_day,
            #     }
            # )

        # print(non_business_days)

        return Response(
            {
                "year": year,
                "month": month,
                "non_business_days": non_business_days,
                "non_business_weekdays": non_business_weekdays,
                # "days": days_meta,
            }
        )


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 재직자 여부 가드
        resp = ensure_active_employee_or_403(user)
        if resp is not None:
            return resp

        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MealMySummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        branch, error_resp = _get_branch_or_error(request)
        if error_resp:
            return error_resp

        ym, error = _normalize_ym(request.query_params.get("ym"))
        if error:
            return _validation_error(error)

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
