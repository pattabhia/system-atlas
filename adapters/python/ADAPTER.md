# Adapter — python (scaffold)

**Kind:** language / build · **Binds when:** Stack Profile language = Python.
**Status:** SCAFFOLD — capability contract defined; implementations pending.

| Capability | Tool (free/OSS, stdlib-friendly) |
|-----------|------|
| resolve_project_structure / resolve_dependencies | `pyproject.toml` / `requirements.txt`, `importlib.metadata` |
| build_source_model / build_call_graph | stdlib **`ast`** / **LibCST** (parse); `jedi` for symbol resolution |
| discover_entrypoints | route scan (Flask `@app.route`, FastAPI `@app.get`, Django urls, Celery tasks) |
| trace_data_state_flow | `ast` walk |
| run_characterization_tests | `pytest` |

Infra capabilities bind per boundary kind. Until built, binds to generic-fallback with a capability gap.
