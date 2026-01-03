import wireup

from test.unit.services.inheritance_test.base import Base


@wireup.injectable
class ObjWithInheritance(Base): ...
