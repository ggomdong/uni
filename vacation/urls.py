from django.urls import path
from . import views

app_name = "vacation"

urlpatterns = [
    path("ledger/", views.ledger, name="ledger"),
    path("ledger/<str:stand_ym>", views.ledger, name="ledger"),
    path("approvals/<str:stand_ym>", views.approvals, name="approvals"),
    path("resignation/<str:stand_ym>", views.resignation, name="resignation"),

    # 설정 화면도 vacation이 책임진다
    path("settings/", views.settings, name="settings"),
]
