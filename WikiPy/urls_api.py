from django.urls import path

from . import views

app_name = 'wikipy_api'
urlpatterns = [
    path('', views.api_handler, name='index'),
]
