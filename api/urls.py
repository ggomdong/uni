from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .views.auth import CustomTokenObtainPairView
from .views.attendance import AttendanceAPIView, MonthlyAttendanceAPIView, NonBusinessDayListAPIView
from .views.beacons import BeaconListAPIView
from .views.work import WorkCreateAPIView
from .views.profile import ProfileAPIView

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('attendance/', AttendanceAPIView.as_view()),
    path('attendance/monthly', MonthlyAttendanceAPIView.as_view()),
    path('beacons/', BeaconListAPIView.as_view()),
    path('work/', WorkCreateAPIView.as_view()),
    path(
        "non-business-days/",
        NonBusinessDayListAPIView.as_view(),
        name="non-business-days",
    ),
    path('profile/', ProfileAPIView.as_view()),
]
