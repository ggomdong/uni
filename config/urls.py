"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from pybo.views import base_views

admin.site.site_header = 'YOU&I Admin'      # 사이트명
admin.site.site_title = 'You&I Admin'       # 브라우저 title 명
admin.site.index_title = '웹사이트 관리'        # 관리화면 메뉴명

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', base_views.index, name='index'),
    path('api/', include('api.urls')),
    path('pybo/', include('pybo.urls')),
    path('common/', include('common.urls')),
    path('wtm/', include('wtm.urls')),
]