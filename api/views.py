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
from .serializers import UserSerializer, AttendanceSerializer, MonthlyAttendanceDaySerializer, WorkSerializer
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


# def build_monthly_attendance_for_user(user, year: int, month: int):
#     """한 사용자에 대한 '월간 일자별 근태' 리스트를 생성."""
#     # 1. 스케줄 조회
#     try:
#         schedule = Schedule.objects.get(
#             user=user, year=str(year), month=f"{month:02d}"
#         )
#     except Schedule.DoesNotExist:
#         return []
#
#     # 2. 근태 기록 조회
#     works = Work.objects.filter(
#         user=user, record_day__year=year, record_day__month=month
#     )
#
#     # 날짜별로 출퇴근 매핑
#     work_map = {}
#     for w in works:
#         day = w.record_day
#         if day not in work_map:
#             work_map[day] = {"I": [], "O": []}
#         work_map[day][w.work_code].append(w)
#
#     results = []
#     days_in_month = monthrange(year, month)[1]
#     today = timezone.now().date()
#
#     # 3. 월간 루프 돌면서 데이터 구성
#     for day in range(1, days_in_month + 1):
#         module: Module = getattr(schedule, f"d{day}", None)
#         record_day = date(year, month, day)
#
#         work_in_list = work_map.get(record_day, {}).get("I", [])
#         work_out_list = work_map.get(record_day, {}).get("O", [])
#
#         work_in = min(work_in_list, key=lambda w: w.record_date) if work_in_list else None
#         work_out = max(work_out_list, key=lambda w: w.record_date) if work_out_list else None
#
#         # 화면용 HH:mm 문자열
#         checkin_time = work_in.record_date.strftime("%H:%M") if work_in else None
#         # 스케줄 종료시각 파싱
#         sched_end_hhmm = module.end_time if (module and module.end_time and module.end_time != "-") else None
#         sched_end_dt = to_dt(record_day, sched_end_hhmm) if sched_end_hhmm else None  # 스케줄 종료 datetime
#
#         # 출근 datetime
#         checkin_dt = to_dt(record_day, checkin_time) if checkin_time else None  # "HH:mm" → dt
#
#         # 퇴근시각 결정 (정책)
#         # 1) 실제 퇴근 로그가 있으면 그대로 사용
#         # 2) 없으면 '어제까지'이고 '출근 ≤ 스케줄 종료'일 때만 스케줄 종료로 보정
#         if work_out:
#             checkout_time = work_out.record_date.strftime("%H:%M")
#         else:
#             if (record_day < today) and sched_end_dt and checkin_dt and (checkin_dt <= sched_end_dt):
#                 checkout_time = sched_end_hhmm
#             else:
#                 checkout_time = None
#
#         checkout_dt = to_dt(record_day, checkout_time) if checkout_time else None  # "HH:mm" → dt
#
#         # === 휴게 반영 유급 세그먼트 생성 ===
#         paid_segments = make_paid_segments(record_day, module)  # (start~end) - (breaks)
#         paid_total = total_minutes(paid_segments)  # 유급세그먼트 총 분
#
#         # === 분 단위 지표 계산 ===
#         late_minutes = minutes_before(checkin_dt, paid_segments) if checkin_dt else 0  # 지각
#         early_leave_minutes = minutes_after(checkout_dt, paid_segments) if checkout_dt else 0  # 조퇴
#         overtime_minutes = compute_overtime_minutes(checkin_dt, checkout_dt, paid_segments)  # 연장
#
#         holiday_minutes = 0
#         if module and module.cat == "휴일근무" and checkin_dt and checkout_dt:
#             holiday_minutes = intersection_minutes(checkin_dt, checkout_dt, paid_segments)  # 휴일근무 분
#
#         # === 상태코드 조합 산출 ===
#         has_checkin = bool(checkin_dt)
#         has_checkout = bool(checkout_dt)
#         # 실 체류 ∩ 유급
#         presence_paid = intersection_minutes(checkin_dt, checkout_dt, paid_segments) if (
#                 has_checkin and has_checkout) else 0
#
#         # 오늘 이후의 상태 판정을 위한 변수 설정
#         is_today = (record_day == today)
#         is_future = (record_day > today)
#
#         if not module:
#             status_codes = ["NOSCHEDULE"]
#         else:
#             cat = module.cat
#
#             # 1) 휴무/오프/스케줄 있는 날 먼저 처리
#             if cat in ("유급휴무", "무급휴무", "OFF"):
#                 # 출퇴근 기록 있으면 오류
#                 if has_checkin or has_checkout:
#                     status_codes = ["ERROR"]
#                 else:
#                     base_map = {"유급휴무": "PAY", "무급휴무": "NOPAY", "OFF": "OFF"}
#                     status_codes = [base_map[cat]]
#
#             elif cat in ("정규근무", "휴일근무"):
#
#                 if is_future:
#                     # 미래: 휴일근무 외에는 아직 결정되지 않음(칩/점 미표시용으로 빈 배열)
#                     status_codes = []
#                     if cat == "휴일근무":
#                         status_codes.append("HOLIDAY")
#
#                 else:
#                     if is_today:
#                         # 오늘: '명백히 잘못'이면 ERROR
#                         is_error = (
#                             (has_checkin and has_checkout and paid_total > 0 and presence_paid == 0)
#                         )
#                     else:
#                         is_error = (
#                             # (1) 출퇴근 기록 없음
#                                 (not has_checkin and not has_checkout) or
#                                 # (2) 유급 교집합 0
#                                 (paid_total > 0 and has_checkin and has_checkout and presence_paid == 0)
#                         )
#
#                     if is_error:
#                         status_codes = ["ERROR"]
#                     else:
#                         status_codes = []
#                         # 휴일근무면, "휴일근무" 상태 설정, 정규근무는 "정규근무"라고 설정하지 않음
#                         if cat == "휴일근무":
#                             status_codes.append("HOLIDAY")
#
#                         # 모디파이어
#                         if late_minutes > 0:
#                             status_codes.append("LATE")
#                         if early_leave_minutes > 0:
#                             status_codes.append("EARLY")
#                         if overtime_minutes > 0:
#                             status_codes.append("OVERTIME")
#
#                         # 정규근무에서 '정상' 부여 규칙
#                         # - 지각/조퇴가 없으면 NORMAL 추가
#                         # - '정상 + 연장' 케이스 허용을 위해, 연장이 있더라도 NORMAL은 함께 둘 수 있음(이때 NORMAL을 앞으로 두어 정렬처리)
#                         if cat == "정규근무" and has_checkin and ("LATE" not in status_codes) and ("EARLY" not in status_codes):
#                             status_codes.insert(0, "NORMAL")
#
#             else:
#                 # 카테고리 정의 외 방어
#                 status_codes = ["NOSCHEDULE"]
#
#         # 라벨(사람 읽기용)
#         status_label = "+".join(STATUS_LABELS.get(c, c) for c in status_codes)
#         status_label_list = [STATUS_LABELS.get(c, c) for c in status_codes]
#
#         # 색상(템플릿 호환용)
#         work_color_code = module.color if module else None
#         work_color_hex = module_colors.get(module.color) if module else None
#
#         results.append({
#             "record_day": record_day,
#             "work_start": module.start_time if module else None,
#             "work_end": module.end_time if module else None,
#             "checkin_time": checkin_time,
#             "checkout_time": checkout_time,
#
#             # 상태(앱은 status_codes/labels 배열을 쓰면 됨)
#             "status": status_label,  # 하위호환용 문자열
#             "status_codes": status_codes,  # ["REGULAR","LATE",...]
#             "status_labels": status_label_list,  # ["정규근무","지각",...]
#
#             # 모듈/색
#             "work_cat": module.cat if module else None,
#             "work_name": module.name if module else None,
#             "work_color_code": work_color_code,
#             "work_color_hex": work_color_hex,
#
#             # 분 단위 지표(휴게 반영)
#             "late_minutes": late_minutes,
#             "early_leave_minutes": early_leave_minutes,
#             "overtime_minutes": overtime_minutes,
#             "holiday_minutes": holiday_minutes,
#
#             # 프런트 편의
#             "is_late": late_minutes > 0,
#             "is_early_checkout": early_leave_minutes > 0,
#             "is_overtime": overtime_minutes > 0,
#         })
#
#     return results


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
