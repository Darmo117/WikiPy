from django.urls import path

from . import views

urlpatterns = [
    path('<str:page_title>', views.page, name='page'),
]
