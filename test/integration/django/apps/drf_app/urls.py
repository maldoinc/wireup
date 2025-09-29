from django.urls import path
from rest_framework.routers import DefaultRouter

from test.integration.django.apps.drf_app import views

router = DefaultRouter()
router.register(r"viewset", views.DRFGreetingViewSet, basename="greeting")

urlpatterns = [
    path("fbv/", views.drf_function_based_view),
    path("cbv/", views.DRFClassBasedView.as_view()),
] + router.urls
