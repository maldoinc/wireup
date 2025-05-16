# Optional Performance Optimization

Optimize dependency injection performance by using a custom APIRoute class. 
This reduces overhead in endpoints that use Wireup injection by avoiding redundant processing.

```python
from fastapi import APIRouter
from wireup.integration.fastapi import WireupRoute

router = APIRouter(route_class=WireupRoute)
```

If you already have a custom route class, you can inherit from WireupRoute instead.

**Under the hood**: FastAPI processes all route parameters, including ones meant for Wireup. 
The WireupRoute class optimizes this by making Wireup-specific parameters only visible to Wireup, 
removing unnecessary processing by FastAPI's dependency injection system.
