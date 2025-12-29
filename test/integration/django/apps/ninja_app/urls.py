from django.urls import path
from ninja import NinjaAPI

from test.integration.django.apps.ninja_app.views import router

api = NinjaAPI(urls_namespace="wireup-ninja-test")
api.add_router("/", router)

urlpatterns = [path("", api.urls)]
