from django.urls import path
from . import views

app_name = 'wtm'

urlpatterns = [
    path('list/', views.work_list, name='work_list'),
    path('module/', views.work_module, name='work_module'),
    path('module_reg/', views.work_module_reg, name='work_module_reg'),
    path('module_modify/<int:module_id>/', views.work_module_modify, name='work_module_modify'),
    path('module_delete/<int:module_id>/', views.work_module_delete, name='work_module_delete'),
    path('status/', views.work_status, name='work_status'),
    path('log/', views.work_log, name='work_log'),
]