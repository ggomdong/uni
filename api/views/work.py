from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from api.serializers import WorkSerializer
from wtm.models import Work
from .common import ensure_active_employee_or_403


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
