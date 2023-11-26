from django.urls import path
from . import views

urlpatterns = [
    path('account/', views.user_list),
    path('account/<username>/', views.user),
    path('login/', views.login),
    path('work/', views.work_record),
]