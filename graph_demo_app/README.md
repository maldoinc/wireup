Run the demo app with:

```bash
uvicorn graph_demo_app.main:app --reload
```

Endpoints:

- `/weather` returns a dependency-injected payload
- `/_wireup/graph` returns the exported graph JSON
- `/_wireup` returns the full-page Cytoscape renderer
