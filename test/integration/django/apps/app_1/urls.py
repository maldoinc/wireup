from django.urls import path

from test.integration.django.apps.app_1 import views

urlpatterns = [
    path("/", views.test),
    path("/inject/", views.test_inject),
    path("/cbv/inject/", views.TestInjectView.as_view()),
]
