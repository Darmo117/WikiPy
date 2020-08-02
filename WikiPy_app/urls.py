from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.page, name='main_page'),
    re_path('(?P<raw_page_title>.*)', views.page, name='page'),
]
