from wireup.integration.django import WireupSettings

DEBUG = True
SECRET_KEY = "ninja_test_secret"  # noqa: S105
ROOT_URLCONF = "test.integration.django_ninja.urls"
INSTALLED_APPS = [
    "wireup.integration.django",
]
MIDDLEWARE = ["wireup.integration.django.wireup_middleware"]
WIREUP = WireupSettings(
    service_modules=["test.shared.shared_services"],
)
