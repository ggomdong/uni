from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.utils import timezone

from common.models import User


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
