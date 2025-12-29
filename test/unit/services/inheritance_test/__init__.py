import wireup

from test.unit.services.inheritance_test.base import Base


@wireup.service
class ObjWithInheritance(Base): ...
