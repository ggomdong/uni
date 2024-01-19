from django.urls import path
from . import views

app_name = 'wtm'

urlpatterns = [
    path('index/', views.index, name='index'),
    path('module/', views.work_module, name='work_module'),
    path('module_reg/', views.work_module_reg, name='work_module_reg'),
    path('module_modify/<int:module_id>/', views.work_module_modify, name='work_module_modify'),
    path('module_delete/<int:module_id>/', views.work_module_delete, name='work_module_delete'),
    path('contract_reg/<int:user_id>', views.work_contract_reg, name='work_contract_reg'),
    path('contract_modify/<int:contract_id>/', views.work_contract_modify, name='work_contract_modify'),
    path('contract_delete/<int:contract_id>/', views.work_contract_delete, name='work_contract_delete'),
    path('list/', views.work_list, name='work_list'),
    path('status/', views.work_status, name='work_status'),
    path('log/', views.work_log, name='work_log'),
]