from datetime import datetime, date

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from wtm.models import Work, Schedule
from wtm.services.attendance import build_monthly_attendance_for_user
from wtm.services.calendar_rules import get_non_business_calendar
from api.serializers import AttendanceSerializer, MonthlyAttendanceDaySerializer

from .common import ensure_active_employee_or_403

_TEST_MODE = False
_TEST_TODAY = datetime(2025, 12, 5).date()
_TEST_NOW = datetime.combine(_TEST_TODAY, datetime.strptime("08:35", "%H:%M").time())


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

        day_numbers, non_business_weekdays = get_non_business_calendar(
            year, month, branch=request.user.branch
        )
        non_business_days = [
            date(year, month, day).strftime("%Y-%m-%d")
            for day in sorted(day_numbers)
        ]

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
