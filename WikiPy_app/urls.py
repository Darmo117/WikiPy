from django.urls import path, re_path

from . import views

app_name = 'wikipy'
urlpatterns = [
    path('', views.page, name='main_page'),
    path('Special:WikiSetup', views.setup_page, name='setup'),
    re_path('(?P<raw_page_title>.*)', views.page, name='page'),
]
