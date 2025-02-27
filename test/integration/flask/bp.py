from typing import Any, Dict

import flask
from typing_extensions import Annotated
from wireup import Inject

from test.integration.flask.services.is_test_service import IsTestService
from test.shared.shared_services.rand import RandomService
from test.shared.shared_services.scoped import ScopedService, ScopedServiceDependency

bp = flask.Blueprint("bp", "bp")


@bp.get("/random")
def random(random: RandomService):
    return {"lucky_number": random.get_random()}


@bp.get("/env")
def env(is_debug: Annotated[bool, Inject(param="DEBUG")], is_test: Annotated[bool, Inject(param="TESTING")]):
    return {"debug": is_debug, "test": is_test}


@bp.get("/not-autowired")
def not_autowired():
    return "not autowired"


@bp.get("/scoped")
def scoped(s1: ScopedService, s2: ScopedServiceDependency, s3: ScopedServiceDependency) -> Dict[str, Any]:
    assert s1.other is s2
    assert s3 is s2

    return {}


@bp.get("/foo")
def foo(foo: IsTestService):
    return {"test": foo.is_test}
