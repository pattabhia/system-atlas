#!/usr/bin/env python3
"""
java_ast.py — Tier-2 source analysis for the java-maven adapter.

Emits, as JSON on stdout, one of:
  --model        per-file source model (packages, classes, methods, fields, imports)
  --callgraph    heuristic caller -> callee edges with a confidence score
  --entrypoints  detected invocation surfaces (annotations / main / runners)

Claude (the runtime) calls this from ADAPTER.md and reads the JSON back.

LIMITATIONS (must be surfaced, never hidden):
  * Call-graph resolution is HEURISTIC and name/type-based, not a compiler- or
    bytecode-derived graph. It resolves callee types via imports, declared local
    variable types, fields and `this`; anything else is emitted with lower
    confidence and `resolved: false`. Overloads and dynamic dispatch are reported
    as-is, not disambiguated. Reflection / proxies / lambdas-as-callbacks are not
    followed. Treat edges as evidence at their stated confidence, not proof.
  * If `javalang` is not installed, this script exits non-zero with a JSON error
    object so the adapter falls back to grep and records a `CAPABILITY` gap.
"""
import argparse
import json
import os
import sys

try:
    import javalang
except Exception as e:  # pragma: no cover - environment dependent
    print(json.dumps({
        "ok": False,
        "error": "javalang_unavailable",
        "detail": str(e),
        "remedy": "pip install javalang  (or use the grep fallback in ADAPTER.md)",
        "capability_gap": "CAPABILITY",
    }))
    sys.exit(2)

ENTRYPOINT_ANNOTATIONS = {
    "RestController", "Controller", "RequestMapping", "GetMapping", "PostMapping",
    "PutMapping", "DeleteMapping", "PatchMapping", "Path", "KafkaListener",
    "JmsListener", "RabbitListener", "Scheduled", "MessageMapping", "EventListener",
    "StreamListener",
}
SKIP_DIRS = {"target", "build", ".git", "node_modules", ".idea", "out"}


def iter_java_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".java"):
                yield os.path.join(dirpath, fn)


def parse_tree(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        return javalang.parse.parse(src), None
    except Exception as e:
        return None, {"file": path, "error": type(e).__name__, "detail": str(e)}


def anno_names(node):
    out = []
    for a in getattr(node, "annotations", []) or []:
        out.append(a.name)
    return out


def method_sig(m):
    params = []
    for p in m.parameters:
        t = getattr(p.type, "name", None) or "var"
        params.append(t)
    ret = getattr(m, "return_type", None)
    ret = getattr(ret, "name", None) if ret else "void"
    return {"name": m.name, "params": params, "return": ret,
            "annotations": anno_names(m),
            "modifiers": sorted(list(getattr(m, "modifiers", []) or []))}


def build_model(root):
    files, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_tree(path)
        if err:
            errors.append(err)
            continue
        pkg = tree.package.name if tree.package else None
        imports = {}
        for imp in tree.imports:
            simple = imp.path.split(".")[-1]
            imports[simple] = imp.path
        classes = []
        for _, node in tree.filter(javalang.tree.TypeDeclaration):
            methods = [method_sig(m) for m in getattr(node, "methods", [])]
            fields = []
            for f in getattr(node, "fields", []):
                ftype = getattr(f.type, "name", None)
                for d in f.declarators:
                    fields.append({"name": d.name, "type": ftype})
            classes.append({
                "name": node.name,
                "kind": type(node).__name__,
                "annotations": anno_names(node),
                "extends": getattr(getattr(node, "extends", None), "name", None)
                           if not isinstance(getattr(node, "extends", None), list) else None,
                "methods": methods,
                "fields": fields,
            })
        files.append({"file": path, "package": pkg,
                      "imports": imports, "classes": classes})
    return {"ok": True, "capability": "build_source_model",
            "root": root, "files": files, "parse_errors": errors,
            "counts": {"files": len(files), "errors": len(errors)}}


def build_callgraph(root):
    edges, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_tree(path)
        if err:
            errors.append(err)
            continue
        pkg = tree.package.name if tree.package else ""
        imports = {imp.path.split(".")[-1]: imp.path for imp in tree.imports}
        for _, cls in tree.filter(javalang.tree.TypeDeclaration):
            # local field name -> declared type, to resolve `field.method()`
            field_types = {}
            for f in getattr(cls, "fields", []):
                ftype = getattr(f.type, "name", None)
                for d in f.declarators:
                    field_types[d.name] = ftype
            for m in getattr(cls, "methods", []):
                caller = f"{pkg}.{cls.name}#{m.name}" if pkg else f"{cls.name}#{m.name}"
                # local var name -> type within this method
                local_types = {}
                if m.body:
                    for _, ld in m.filter(javalang.tree.LocalVariableDeclaration):
                        lt = getattr(ld.type, "name", None)
                        for d in ld.declarators:
                            local_types[d.name] = lt
                    for _, inv in m.filter(javalang.tree.MethodInvocation):
                        qualifier = inv.qualifier or ""
                        member = inv.member
                        owner_type, resolved, conf = None, False, 0.3
                        if qualifier in ("", "this"):
                            owner_type, resolved, conf = cls.name, True, 0.8
                        elif qualifier in local_types:
                            owner_type, resolved, conf = local_types[qualifier], True, 0.7
                        elif qualifier in field_types:
                            owner_type, resolved, conf = field_types[qualifier], True, 0.7
                        elif qualifier and qualifier[0].isupper():
                            # static call on a type name
                            owner_type, resolved, conf = qualifier, True, 0.6
                        fqn = imports.get(owner_type, owner_type) if owner_type else None
                        edges.append({
                            "caller": caller,
                            "callee": {"owner": owner_type, "owner_fqn": fqn,
                                       "method": member, "qualifier": qualifier},
                            "resolved": resolved,
                            "confidence": conf,
                        })
    return {"ok": True, "capability": "build_call_graph",
            "root": root, "edges": edges, "parse_errors": errors,
            "resolution": "heuristic-name-type",
            "counts": {"edges": len(edges),
                       "unresolved": sum(1 for e in edges if not e["resolved"]),
                       "errors": len(errors)}}


def find_entrypoints(root):
    hits, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_tree(path)
        if err:
            errors.append(err)
            continue
        pkg = tree.package.name if tree.package else ""
        for _, cls in tree.filter(javalang.tree.TypeDeclaration):
            cls_annos = set(anno_names(cls))
            implements = [getattr(i, "name", None) for i in (getattr(cls, "implements", None) or [])]
            for m in getattr(cls, "methods", []):
                m_annos = set(anno_names(m))
                surfaces = (cls_annos | m_annos) & ENTRYPOINT_ANNOTATIONS
                is_main = (m.name == "main" and "static" in (m.modifiers or set())
                           and "public" in (m.modifiers or set()))
                is_runner = "run" == m.name and "CommandLineRunner" in implements
                if surfaces or is_main or is_runner:
                    hits.append({
                        "file": path,
                        "type": f"{pkg}.{cls.name}" if pkg else cls.name,
                        "method": m.name,
                        "surfaces": sorted(surfaces),
                        "main": is_main, "runner": is_runner,
                        "class_annotations": sorted(cls_annos),
                    })
    return {"ok": True, "capability": "discover_entrypoints",
            "root": root, "entrypoints": hits, "parse_errors": errors,
            "counts": {"entrypoints": len(hits), "errors": len(errors)}}


def main():
    ap = argparse.ArgumentParser(description="java-maven Tier-2 source analysis")
    ap.add_argument("--root", required=True, help="source root to analyze")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--model", action="store_true")
    g.add_argument("--callgraph", action="store_true")
    g.add_argument("--entrypoints", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(json.dumps({"ok": False, "error": "root_not_found", "root": args.root}))
        sys.exit(1)

    if args.model:
        result = build_model(args.root)
    elif args.callgraph:
        result = build_callgraph(args.root)
    else:
        result = find_entrypoints(args.root)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
