from django.urls import path

from test.integration.django.apps.app_1 import views

urlpatterns = [
    path('/', views.test),
]