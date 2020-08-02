from django.urls import path

from . import views

urlpatterns = [
    path('', views.handle404, name='404'),
]
