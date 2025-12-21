from django.db import transaction
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
from wtm.models import Work, Schedule, Beacon
from wtm.services.attendance import build_monthly_attendance_for_user

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


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        device_id = self.context['request'].data.get('device_id')

        if not device_id:
            raise ValidationError("기기 식별값이 누락되었습니다.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthenticationFailed("아이디 혹은 비밀번호가 올바르지 않습니다.")

        # 디바이스 검증
        if user.device_id:
            if user.device_id != device_id:
                raise ValidationError("등록되지 않은 기기입니다. 관리자에게 문의하세요.")
        else:
            user.device_id = device_id
            user.save()

        return super().validate(attrs)


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
        checkin = Work.objects.filter(user=user, work_code='I', record_day=today).order_by('record_date').first()
        checkout = Work.objects.filter(user=user, work_code='O', record_day=today).order_by('-record_date').first()

        # 오늘 근무표 정보 조회
        try:
            schedule = Schedule.objects.get(user=user, year=str(today.year), month=f"{today.month:02}")
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
            checkin_exists = Work.objects.select_for_update().filter(user=user, work_code='I', record_day=today).exists()

            # 근태기록이 없으면 출근, 있으면 퇴근으로 설정
            work_code = 'I' if not checkin_exists else 'O'

            # Work 로그 저장
            serializer = WorkSerializer(data={
                'user': user.id,
                'work_code': work_code,
            })

            if serializer.is_valid():
                work = serializer.save()
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

        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # 1) Holiday 테이블 (법정 공휴일)
        holiday_qs = Holiday.objects.filter(
            holiday__range=(first_day, last_day)
        ).order_by("holiday")
        holiday_map = {h.holiday: h.holiday_name for h in holiday_qs}

        # 2) Business 테이블 (요일별 영업/비영업 패턴)
        business = (
            Business.objects.filter(stand_date__lte=last_day)
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
