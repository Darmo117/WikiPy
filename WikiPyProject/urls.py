"""WikiPyProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.urls import path, re_path, include
from django.views.generic.base import RedirectView

from WikiPy import apps

urlpatterns = [
    path('', RedirectView.as_view(url='wiki/', permanent=True)),
    path('wiki', RedirectView.as_view(url='wiki/', permanent=True)),
    path('wiki/', include(apps.WikiPyConfig.name + '.urls')),
    path('api', RedirectView.as_view(url='api/', permanent=True)),
    path('api/', include(apps.WikiPyConfig.name + '.urls_api')),
    re_path(r'.*', include(apps.WikiPyConfig.name + '.urls_404')),
]

handler500 = apps.WikiPyConfig.name + '.views.handle500'
