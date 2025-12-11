from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'common'

urlpatterns = [
    path('login/', views.WebLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('user_list/', views.user_list, name='user_list'),
    path('nametag/<str:emp_name>/<str:position>', views.nametag, name='nametag'),
    path('user_modify/<int:user_id>/', views.user_modify, name='user_modify'),
    path('user_modify/<int:user_id>/change-password/', views.password_change, name='password_change'),
    path('user_modify/<int:user_id>/reset-device/', views.reset_device, name='reset_device'),
    path('dept/', views.dept, name='dept'),
    path('position/', views.position, name='position'),
    path('holiday/', views.holiday, name='holiday'),
    path('business/', views.business, name='business'),
    path('code/', views.code, name='code'),
]