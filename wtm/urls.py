from django.urls import path
from . import views

app_name = 'wtm'

urlpatterns = [
    path('index/', views.index, name='index'),
    path('index/<str:stand_day>', views.index, name='index'),
    path('module/', views.work_module, name='work_module'),
    path('module_reg/', views.work_module_reg, name='work_module_reg'),
    path('module_modify/<int:module_id>/', views.work_module_modify, name='work_module_modify'),
    path('module_delete/<int:module_id>/', views.work_module_delete, name='work_module_delete'),
    path('contract_reg/<int:user_id>', views.work_contract_reg, name='work_contract_reg'),
    # path('contract_modify/<int:contract_id>/', views.work_contract_modify, name='work_contract_modify'),
    path(r'^contract_modify/(?P<contract_id>[0-9]*)/$', views.work_contract_modify, name='work_contract_modify'),
    path('contract_delete/<int:contract_id>/', views.work_contract_delete, name='work_contract_delete'),
    path('schedule/', views.work_schedule, name='work_schedule'),
    path('schedule/<str:stand_ym>', views.work_schedule, name='work_schedule'),
    path('schedule_reg/<str:stand_ym>/', views.work_schedule_reg, name='work_schedule_reg'),
    path('schedule_modify/<str:stand_ym>/', views.work_schedule_modify, name='work_schedule_modify'),
    path('schedule_delete/<str:stand_ym>/', views.work_schedule_delete, name='work_schedule_delete'),
    path('schedule_popup/', views.work_schedule_popup, name='work_schedule_popup'),
    path('status/', views.work_status, name='work_status'),
    path('log/', views.work_log, name='work_log'),
    path('log/<str:stand_day>', views.work_log, name='work_log'),
    path('meal/', views.work_meal, name='work_meal'),
    path('meal/<str:stand_year>', views.work_meal, name='work_meal'),
]