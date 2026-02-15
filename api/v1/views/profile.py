from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from api.v1.serializers import UserProfileSerializer
from .common import ensure_active_employee_or_403


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
