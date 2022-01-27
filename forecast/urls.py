"""forecast URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from forecast_app.views import download, run_calculation, test_saving

from rest_framework import routers

router = routers.DefaultRouter()
#user_detail = GetRasterTiff.as_view({'get': 'download'})
#router.register('get_tiff', user_detail, 'tiff')

urlpatterns = [
    path('get_tiff', download),
    path('test_calc', run_calculation),
    path('test_saving', test_saving),
    path('admin/', admin.site.urls),
]
