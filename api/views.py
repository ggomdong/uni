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
from datetime import datetime
from .serializers import UserProfileSerializer, AttendanceSerializer, MonthlyAttendanceDaySerializer, WorkSerializer
from common.models import User
from wtm.models import Work, Schedule
from wtm.services.attendance import build_monthly_attendance_for_user


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

        # print(data)

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
        results = build_monthly_attendance_for_user(user, year, month)

        print(results)

        serializer = MonthlyAttendanceDaySerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
