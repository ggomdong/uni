from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed
from common.models import User
from wtm.models import Work
from .serializers import UserSerializer, WorkSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return response
        except AuthenticationFailed as e:
            return Response(
                {"error": "invalid_credentials", "message": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except InvalidToken as e:
            return Response(
                {"error": "token_expired", "message": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class Me(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class WorkRecord(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 데이터 유효성 확인
        username = request.data.get('username')
        work_code = request.data.get('work_code')

        if not username or not work_code:
            return Response({"error": "ID(username)와 근태구분(work_code)이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "존재하지 않는 사용자입니다."}, status=status.HTTP_404_NOT_FOUND)

        # Serializer 초기화
        serializer = WorkSerializer(data={
            'user': user.id,  # ID를 전달해야 함
            'work_code': work_code,
            'record_date': timezone.now()
        })

        # 유효성 검사
        if serializer.is_valid():
            work = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)