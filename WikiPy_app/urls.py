from django.urls import path

from . import views

urlpatterns = [
    path('', views.page, name='page'),
    path('<str:raw_page_title>', views.page, name='page'),
]
