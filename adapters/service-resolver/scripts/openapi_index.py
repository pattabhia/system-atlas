#!/usr/bin/env python3
"""
openapi_index.py — normalize OpenAPI/Swagger specs into a flat endpoint index
for the service-resolver adapter's match step (resolve_service_target).

Usage:
  python3 openapi_index.py <spec.json|spec.yaml|directory> > openapi-index.json

Output: {"ok": true, "endpoints": [{method, path, path_norm, operationId,
         tags, service, source}], "specs": N, "errors": [...]}

Notes / limitations:
  * Handles OpenAPI 2 (`swagger`) and 3 (`openapi`). `$ref` bodies are NOT
    dereferenced — only routing metadata (method/path/operationId) is indexed,
    which is all the resolver needs to match a client call to a provider.
  * YAML needs `pyyaml`; if it's missing, YAML specs are skipped with an error
    entry and JSON specs still index (degrade, don't fail).
"""
import argparse
import json
import os
import sys

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}

try:
    import yaml  # optional
    _HAVE_YAML = True
except Exception:
    _HAVE_YAML = False


def norm_path(p):
    # /accounts/{id}  ->  /accounts/{}   (variable-agnostic for matching)
    out, depth = [], 0
    buf = ""
    for ch in p:
        if ch == "{":
            depth += 1
            if depth == 1:
                out.append("{}")
        elif ch == "}":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    # also collapse :param and %s style
    s = "".join(out)
    return s


def load_spec(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if path.lower().endswith((".yaml", ".yml")):
        if not _HAVE_YAML:
            raise RuntimeError("pyyaml_unavailable")
        return yaml.safe_load(text)
    return json.loads(text)


def index_spec(doc, source):
    endpoints = []
    if not isinstance(doc, dict):
        return endpoints
    service = (doc.get("info", {}) or {}).get("title")
    base = ""
    if "basePath" in doc:  # OpenAPI 2
        base = doc.get("basePath") or ""
    elif isinstance(doc.get("servers"), list) and doc["servers"]:
        # OpenAPI 3: take path component of first server url
        url = doc["servers"][0].get("url", "")
        base = url[url.find("/", url.find("//") + 2):] if "//" in url else url
        if base in ("/", None):
            base = ""
    for raw_path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        full = (base.rstrip("/") + raw_path) if base else raw_path
        for method, op in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                continue
            endpoints.append({
                "method": method.upper(),
                "path": full,
                "path_norm": norm_path(full),
                "operationId": op.get("operationId"),
                "tags": op.get("tags", []),
                "service": service,
                "source": source,
            })
    return endpoints


def iter_specs(target):
    if os.path.isfile(target):
        yield target
        return
    for dp, dn, fn in os.walk(target):
        dn[:] = [d for d in dn if d not in {"target", "build", "node_modules", ".git"}]
        for f in fn:
            low = f.lower()
            if (("openapi" in low or "swagger" in low or "api-docs" in low)
                    and low.endswith((".json", ".yaml", ".yml"))):
                yield os.path.join(dp, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="spec file or directory to scan")
    args = ap.parse_args()

    endpoints, errors, n = [], [], 0
    for spec in iter_specs(args.target):
        try:
            doc = load_spec(spec)
            endpoints.extend(index_spec(doc, spec))
            n += 1
        except Exception as e:
            errors.append({"spec": spec, "error": type(e).__name__, "detail": str(e)})
    json.dump({"ok": True, "specs": n, "endpoints": endpoints, "errors": errors,
               "yaml_supported": _HAVE_YAML}, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
