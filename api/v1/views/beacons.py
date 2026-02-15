from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from api.v1.serializers import BeaconSerializer
from wtm.models import Beacon


class BeaconListAPIView(APIView):
    """
    내 지점 비콘 목록
    GET /api/beacons

    - 인증된 사용자(request.user)의 User.branch 기준으로 필터
    - is_active = True
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
