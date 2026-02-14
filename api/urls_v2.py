from django.urls import path
from .views.meals import (
    MealMySummaryAPIView,
    MealMyItemsAPIView,
    MealOptionsAPIView,
    MealClaimCreateAPIView,
    MealClaimDetailAPIView,
)

urlpatterns = [
    path("meals/my/summary/", MealMySummaryAPIView.as_view()),
    path("meals/my/items/", MealMyItemsAPIView.as_view()),
    path("meals/options/", MealOptionsAPIView.as_view()),
    path("meals/claims/", MealClaimCreateAPIView.as_view()),
    path("meals/claims/<int:claim_id>/", MealClaimDetailAPIView.as_view()),
]
