from django.urls import path
from . import views

app_name = 'wtm'

urlpatterns = [
    path('list/', views.work_list, name='work_list'),
]