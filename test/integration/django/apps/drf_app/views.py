from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from wireup import Injected
from wireup.integration.django import inject

from test.shared.shared_services.greeter import GreeterService


@api_view(["GET"])
@inject
def drf_function_based_view(request: Request, greeter: Injected[GreeterService]) -> Response:
    name = request.query_params.get("name", "Guest")
    greeting = greeter.greet(name)
    return Response({"message": f"FBV: {greeting}"})


class DRFClassBasedView(APIView):
    @inject
    def get(self, request: Request, greeter: Injected[GreeterService]) -> Response:
        name = request.query_params.get("name", "Guest")
        greeting = greeter.greet(name)
        return Response({"message": f"CBV: {greeting}"})


class DRFGreetingViewSet(ViewSet):
    @inject
    def list(self, request: Request, greeter: Injected[GreeterService]) -> Response:
        name = request.query_params.get("name", "Guest")
        greeting = greeter.greet(name)
        return Response({"message": f"ViewSet: {greeting}"})
