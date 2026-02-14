from django.urls import path
from . import views

urlpatterns = [
    path("meals/my/summary/", views.MealMySummaryAPIView.as_view()),
    path("meals/my/items/", views.MealMyItemsAPIView.as_view()),
    path("meals/options/", views.MealOptionsAPIView.as_view()),
    path("meals/claims/", views.MealClaimCreateAPIView.as_view()),
    path("meals/claims/<int:claim_id>/", views.MealClaimDetailAPIView.as_view()),
]
