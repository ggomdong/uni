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
from datetime import datetime, date
from calendar import monthrange
from .serializers import UserSerializer, AttendanceSerializer, AttendanceDaySerializer, WorkSerializer
from common.models import User
from common.context_processors import module_colors
from wtm.models import Work, Schedule, Module


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
            out_date__lte=today
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        TEST_MODE = False

        if TEST_MODE:
            today = datetime(2025, 8, 6).date()
            now = datetime.combine(today, datetime.strptime("13:00", "%H:%M").time())
        else:
            today = timezone.now().date()
            now = timezone.now()

        # 출근/퇴근 기록 조회
        checkin = Work.objects.filter(user=user, work_code='I', record_day=today).order_by('record_date').first()
        checkout = Work.objects.filter(user=user, work_code='O', record_day=today).order_by('-record_date').first()

        # 오늘 스케쥴 정보 조회
        try:
            schedule = Schedule.objects.get(user=user, year=str(today.year), month=f"{today.month:02}")
            module = getattr(schedule, f"d{today.day}", None)
        except Schedule.DoesNotExist:
            module = None

        # 시작/종료 시간 파싱. '-'이면 null로 처리
        work_start = module.start_time if module and module.start_time and module.start_time != '-' else None
        work_end = module.end_time if module and module.end_time and module.end_time != '-' else None

        # 현재 시간 기준 조퇴/연장근무 판단. True(조퇴), False(연장근무 후 퇴근)
        is_early_checkout = False

        if work_end and checkin:
            scheduled_end = datetime.combine(today, datetime.strptime(work_end, "%H:%M").time())
            if now < scheduled_end:
                is_early_checkout = True
            elif now > scheduled_end:
                is_early_checkout = False

        data = {
            "emp_name": user.emp_name,
            "work_start": work_start,
            "work_end": work_end,
            "checkin_time": checkin.record_date if checkin else None,
            "checkout_time": checkout.record_date if checkout else None,
            "is_early_checkout": is_early_checkout,
        }

        print(data)

        serializer = AttendanceSerializer(data)
        return Response(serializer.data)


class MonthlyAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()

        try:
            year = int(request.query_params.get("year", now.year))
            month = int(request.query_params.get("month", now.month))
        except ValueError:
            return Response(
                {"error": "year, month는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. 스케줄 조회
        try:
            schedule = Schedule.objects.get(
                user=user, year=str(year), month=f"{month:02d}"
            )
        except Schedule.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        # 2. 근태 기록 조회
        works = Work.objects.filter(
            user=user, record_day__year=year, record_day__month=month
        )

        # 날짜별로 출퇴근 나누기
        work_map = {}
        for w in works:
            day = w.record_day
            if day not in work_map:
                work_map[day] = {"I": [], "O": []}
            work_map[day][w.work_code].append(w)

        results = []
        days_in_month = monthrange(year, month)[1]

        # 3. 월간 루프 돌면서 데이터 구성
        for day in range(1, days_in_month + 1):
            module: Module = getattr(schedule, f"d{day}", None)
            record_day = date(year, month, day)

            work_in_list = work_map.get(record_day, {}).get("I", [])
            work_out_list = work_map.get(record_day, {}).get("O", [])

            work_in = min(work_in_list, key=lambda w: w.record_date) if work_in_list else None
            work_out = max(work_out_list, key=lambda w: w.record_date) if work_out_list else None

            checkin_time = work_in.record_date.strftime("%H:%M") if work_in else None
            if work_in:
                if work_out:
                    checkout_time = work_out.record_date.strftime("%H:%M")
                else:
                    checkout_time = module.end_time if module else None
            else:
                checkout_time = None

            # minutes 계산
            late_minutes = early_leave_minutes = overtime_minutes = holiday_minutes = 0

            if module and module.cat in ["정규근무", "휴일근무"]:
                fmt = "%H:%M"

                if work_in:
                    work_start_dt = datetime.strptime(module.start_time, fmt)
                    checkin_dt = datetime.strptime(checkin_time, fmt)
                    diff = (checkin_dt - work_start_dt).total_seconds() / 60
                    if diff > 0:
                        late_minutes = int(diff)

                if checkout_time:
                    work_end_dt = datetime.strptime(module.end_time, fmt)
                    checkout_dt = datetime.strptime(checkout_time, fmt)
                    diff = (work_end_dt - checkout_dt).total_seconds() / 60
                    if diff > 0:
                        early_leave_minutes = int(diff)

                    diff = (checkout_dt - work_end_dt).total_seconds() / 60
                    if diff > 0:
                        overtime_minutes = int(diff)

                if module.cat == "휴일근무" and work_in and checkout_time:
                    checkin_dt = datetime.strptime(checkin_time, fmt)
                    checkout_dt = datetime.strptime(checkout_time, fmt)
                    diff = (checkout_dt - checkin_dt).total_seconds() / 60
                    if diff > 0:
                        holiday_minutes = int(diff)

            # status 구분 (9가지)
            if not module:
                status_str = "스케쥴없음"
            elif module.cat == "OFF":
                status_str = "OFF"
            elif module.cat == "무급휴무":
                status_str = "무급휴무"
            elif module.cat == "유급휴무":
                status_str = "유급휴무"
            elif module.cat in ["정규근무", "휴일근무"]:
                if not work_in:
                    status_str = "결근"
                else:
                    if late_minutes > 0:
                        status_str = "지각"
                    elif early_leave_minutes > 0:
                        status_str = "조퇴"
                    elif overtime_minutes > 0:
                        status_str = "연장"
                    elif module.cat == "휴일근무":
                        status_str = "휴일근무"
                    else:
                        status_str = "정상"
            else:
                status_str = "스케쥴없음"  # 방어 처리

            work_color_code = module.color if module else None
            work_color_hex = module_colors.get(module.color) if module else None

            results.append({
                "record_day": record_day,
                "work_start": module.start_time if module else None,
                "work_end": module.end_time if module else None,
                "checkin_time": checkin_time,
                "checkout_time": checkout_time,
                "status": status_str,  # 9가지 상태(스케쥴없음, OFF, 무급휴무, 유급휴무, 정상, 결근, 지각, 조퇴, 연장)
                "work_cat": module.cat if module else None,
                "work_name": module.name if module else None,
                "work_color_code": work_color_code,
                "work_color_hex": work_color_hex,
                "late_minutes": late_minutes,
                "early_leave_minutes": early_leave_minutes,
                "overtime_minutes": overtime_minutes,
                "holiday_minutes": holiday_minutes,
            })

        print(results)

        return Response(results, status=status.HTTP_200_OK)


class WorkCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user
        now = timezone.now()
        today = now.date()

        with transaction.atomic():
            # 오늘 출근 여부 확인
            checkin_exists = Work.objects.select_for_update().filter(user=user, work_code='I', record_day=today).exists()

            # 출근 기록이 없으면 출근, 있으면 퇴근으로 설정
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


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)
