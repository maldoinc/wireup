from django.urls import path
from ninja import NinjaAPI

from test.integration.django_ninja.views import router

api = NinjaAPI(urls_namespace="wireup-ninja-test")
api.add_router("/", router)

# api.urls returns (patterns, app_name, namespace) - use path() directly
urlpatterns = [
    path("", api.urls),
]
