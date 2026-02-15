from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.v1.views.attendance import (
    AttendanceAPIView,
    MonthlyAttendanceAPIView,
    NonBusinessDayListAPIView,
)
from api.v1.views.auth import CustomTokenObtainPairView
from api.v1.views.beacons import BeaconListAPIView
from api.v1.views.meals import (
    MealClaimCreateAPIView,
    MealClaimDetailAPIView,
    MealMyItemsAPIView,
    MealMySummaryAPIView,
    MealOptionsAPIView,
)
from api.v1.views.profile import ProfileAPIView
from api.v1.views.work import WorkCreateAPIView

urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("attendance/", AttendanceAPIView.as_view()),
    path("attendance/monthly", MonthlyAttendanceAPIView.as_view()),
    path("beacons/", BeaconListAPIView.as_view()),
    path("work/", WorkCreateAPIView.as_view()),
    path(
        "non-business-days/",
        NonBusinessDayListAPIView.as_view(),
        name="non-business-days",
    ),
    path("profile/", ProfileAPIView.as_view()),
    path("meals/my/summary/", MealMySummaryAPIView.as_view()),
    path("meals/my/items/", MealMyItemsAPIView.as_view()),
    path("meals/options/", MealOptionsAPIView.as_view()),
    path("meals/claims/", MealClaimCreateAPIView.as_view()),
    path("meals/claims/<int:claim_id>/", MealClaimDetailAPIView.as_view()),
]
