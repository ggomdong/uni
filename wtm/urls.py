from django.urls import path
from wtm.views.index import index
from wtm.views.stat import (
    work_status,
    work_status_excel,
    work_metric,
)
from wtm.views.module import (
    work_module,
    work_module_reorder,
    work_module_reg,
    work_module_modify,
    work_module_delete,
)
from wtm.views.contract import (
    work_contract_reg,
    work_contract_modify,
    work_contract_delete,
)
from wtm.views.schedule import (
    work_schedule,
    work_schedule_reg,
    work_schedule_modify,
    work_schedule_delete,
    work_schedule_popup,
)
from wtm.views.log import (
    work_log,
    work_log_save,
    work_log_delete,
)
from wtm.views.meal import work_meal_status, work_meal_json

from wtm.views.vacation import work_vacation_json

from wtm.views.etc import work_privacy

app_name = 'wtm'

urlpatterns = [
    path('index/', index, name='index'),
    path('index/<str:stand_day>', index, name='index'),
    path('module/', work_module, name='work_module'),
    path('work/module/reorder/', work_module_reorder, name='work_module_reorder'),
    path('module_reg/', work_module_reg, name='work_module_reg'),
    path('module_modify/<int:module_id>/', work_module_modify, name='work_module_modify'),
    path('module_delete/<int:module_id>/', work_module_delete, name='work_module_delete'),
    path('contract_reg/<int:user_id>', work_contract_reg, name='work_contract_reg'),
    path('contract_modify/<int:contract_id>/', work_contract_modify, name='work_contract_modify'),
    # path(r'^contract_modify/(?P<contract_id>[0-9]*)/$', work_contract_modify, name='work_contract_modify'),
    path('contract_delete/<int:contract_id>/', work_contract_delete, name='work_contract_delete'),
    path('schedule/', work_schedule, name='work_schedule'),
    path('schedule/<str:stand_ym>', work_schedule, name='work_schedule'),
    path('schedule_reg/<str:stand_ym>/', work_schedule_reg, name='work_schedule_reg'),
    path('schedule_modify/<str:stand_ym>/', work_schedule_modify, name='work_schedule_modify'),
    path('schedule_delete/<str:stand_ym>/', work_schedule_delete, name='work_schedule_delete'),
    path('schedule_popup/', work_schedule_popup, name='work_schedule_popup'),
    path('status/', work_status, name='work_status'),
    path("status/<str:stand_ym>", work_status, name="work_status"),
    path('status/excel/', work_status_excel, name='work_status_excel'),
    path("status/excel/<str:stand_ym>", work_status_excel, name="work_status_excel"),
    path("status/<str:metric>/", work_metric, name="work_metric"),
    path("status/<str:metric>/<str:stand_ym>", work_metric, name="work_metric"),
    path('log/', work_log, name='work_log'),
    path('log/<str:stand_day>', work_log, name='work_log'),
    path('log/save/', work_log_save, name='work_log_save'),
    path('log/<int:log_id>/delete/', work_log_delete, name='work_log_delete'),
    path('meal/', work_meal_json, name='work_meal_json'),
    path('meal/<str:stand_ym>', work_meal_json, name='work_meal_json'),
    path('meal_status/', work_meal_status, name='work_meal_status'),
    path('meal_status/<str:stand_ym>', work_meal_status, name='work_meal_status'),
    path("vacation/<str:year>/", work_vacation_json, name="work_vacation_json"),
    path('privacy/', work_privacy, name='work_privacy'),
]