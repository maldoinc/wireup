from django.urls import path

from test.integration.django.apps.app_2 import views

urlpatterns = [
    path("/", views.test),
]
