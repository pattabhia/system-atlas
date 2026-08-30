#!/usr/bin/env python3
"""
java_ast.py — Tier-2 source analysis for the java-maven adapter (Stage A).

Parser: tree-sitter + tree-sitter-java (MIT). Full Java 21 grammar — records,
sealed types, switch expressions, text blocks all parse. This replaces the older
javalang backend, which could not parse Java 14+ syntax (gap CG-01).

Emits, as JSON on stdout, one of:
  --model        per-file source model (packages, classes, methods, fields, imports)
  --callgraph    heuristic caller -> callee edges with a confidence score
  --entrypoints  detected invocation surfaces (annotations / main / runners)

LIMITATIONS (must be surfaced, never hidden):
  * tree-sitter PARSES Java 21 fully, but does NOT resolve symbols/types. Call-graph
    resolution here is still HEURISTIC (name/type based via imports, local-var and
    field types, `this`, static type names). Overloads, generics, inheritance and
    cross-jar targets are NOT resolved — those need the Stage B JavaParser+SymbolSolver
    helper (adapters/java-maven/callgraph-jvm) which emits sound, resolved edges.
    Edges here carry a `confidence`; `resolved: false` marks unresolved qualifiers.
  * If tree-sitter is unavailable, this exits non-zero with a JSON error object so the
    adapter falls back to grep and records a CAPABILITY gap.
"""
import argparse
import json
import os
import sys

try:
    import tree_sitter_java as tsjava
    from tree_sitter import Language, Parser
    _LANG = Language(tsjava.language())
except Exception as e:  # pragma: no cover - environment dependent
    print(json.dumps({
        "ok": False,
        "error": "tree_sitter_unavailable",
        "detail": str(e),
        "remedy": "pip install tree-sitter tree-sitter-java  (or use the grep fallback in ADAPTER.md)",
        "capability_gap": "CAPABILITY",
    }))
    sys.exit(2)

ENTRYPOINT_ANNOTATIONS = {
    "RestController", "Controller", "RequestMapping", "GetMapping", "PostMapping",
    "PutMapping", "DeleteMapping", "PatchMapping", "Path", "KafkaListener",
    "JmsListener", "RabbitListener", "Scheduled", "MessageMapping", "EventListener",
    "StreamListener", "KafkaHandler", "SqsListener", "Incoming",
}
TYPE_KINDS = {"class_declaration", "interface_declaration", "enum_declaration",
              "record_declaration", "annotation_type_declaration"}
SKIP_DIRS = {"target", "build", ".git", "node_modules", ".idea", "out"}


def make_parser():
    try:
        return Parser(_LANG)
    except TypeError:  # older binding
        p = Parser(); p.language = _LANG
        return p


def iter_java_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".java"):
                yield os.path.join(dirpath, fn)


def txt(node):
    return node.text.decode("utf-8", "replace") if node is not None else None


def field(node, name):
    return node.child_by_field_name(name)


def walk(node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def _modifiers_node(decl):
    return next((c for c in decl.children if c.type == "modifiers"), None)


def annotations(decl):
    out, mods = [], _modifiers_node(decl)
    if mods:
        for c in mods.children:
            if c.type in ("marker_annotation", "annotation"):
                nm = field(c, "name")
                if nm is not None:
                    out.append(txt(nm).split(".")[-1])
    return out


def modifier_keywords(decl):
    out, mods = [], _modifiers_node(decl)
    if mods:
        for c in mods.children:
            if c.type not in ("marker_annotation", "annotation"):
                out.append(txt(c))
    return out


def type_name(decl):
    return txt(field(decl, "name"))


def methods_of(decl):
    body = field(decl, "body")
    if body is None:
        return []
    return [c for c in body.children if c.type == "method_declaration"]


def fields_of(decl):
    body = field(decl, "body")
    res = []
    if body is None:
        return res
    for c in body.children:
        if c.type == "field_declaration":
            ftype = txt(field(c, "type"))
            for vd in c.children:
                if vd.type == "variable_declarator":
                    res.append({"name": txt(field(vd, "name")), "type": ftype})
    return res


def method_sig(m):
    params = []
    fp = field(m, "parameters")
    if fp is not None:
        for p in fp.children:
            if p.type in ("formal_parameter", "spread_parameter"):
                params.append(txt(field(p, "type")) or "var")
    return {"name": txt(field(m, "name")),
            "params": params,
            "return": txt(field(m, "type")) or "void",
            "annotations": annotations(m),
            "modifiers": modifier_keywords(m)}


def implemented_interfaces(decl):
    out = []
    node = field(decl, "interfaces") or field(decl, "super_interfaces")
    if node is not None:
        for n in walk(node):
            if n.type == "type_identifier":
                out.append(txt(n))
    return out


def parse_file(parser, path):
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        tree = parser.parse(data)
        # tree-sitter never throws on bad syntax; it inserts ERROR nodes.
        return tree, None
    except Exception as e:
        return None, {"file": path, "error": type(e).__name__, "detail": str(e)}


def has_errors(tree):
    return tree.root_node.has_error


def file_package_imports(root_node):
    pkg, imports = None, {}
    for c in root_node.children:
        if c.type == "package_declaration":
            for n in walk(c):
                if n.type in ("scoped_identifier", "identifier"):
                    pkg = txt(n); break
        elif c.type == "import_declaration":
            path = None
            for n in c.children:
                if n.type in ("scoped_identifier", "identifier"):
                    path = txt(n)
            if path:
                imports[path.split(".")[-1]] = path
    return pkg, imports


def build_model(root):
    parser = make_parser()
    files, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_file(parser, path)
        if err:
            errors.append(err); continue
        pkg, imports = file_package_imports(tree.root_node)
        classes = []
        for decl in (n for n in walk(tree.root_node) if n.type in TYPE_KINDS):
            classes.append({
                "name": type_name(decl),
                "kind": decl.type,
                "annotations": annotations(decl),
                "extends": txt(field(decl, "superclass")),
                "implements": implemented_interfaces(decl),
                "methods": [method_sig(m) for m in methods_of(decl)],
                "fields": fields_of(decl),
            })
        files.append({"file": path, "package": pkg, "imports": imports,
                      "classes": classes,
                      "parse_incomplete": bool(tree.root_node.has_error)})
    return {"ok": True, "capability": "build_source_model", "parser": "tree-sitter-java",
            "root": root, "files": files, "parse_errors": errors,
            "counts": {"files": len(files), "errors": len(errors),
                       "with_syntax_errors": sum(1 for f in files if f["parse_incomplete"])}}


def build_callgraph(root):
    parser = make_parser()
    edges, errors, incomplete = [], [], 0
    for path in iter_java_files(root):
        tree, err = parse_file(parser, path)
        if err:
            errors.append(err); continue
        if tree.root_node.has_error:
            incomplete += 1
        pkg, imports = file_package_imports(tree.root_node)
        for cls in (n for n in walk(tree.root_node) if n.type in TYPE_KINDS):
            cname = type_name(cls)
            field_types = {f["name"]: f["type"] for f in fields_of(cls)}
            for m in methods_of(cls):
                caller = f"{pkg}.{cname}#{txt(field(m,'name'))}" if pkg else f"{cname}#{txt(field(m,'name'))}"
                body = field(m, "body")
                if body is None:
                    continue
                local_types = {}
                for n in walk(body):
                    if n.type == "local_variable_declaration":
                        lt = txt(field(n, "type"))
                        for vd in n.children:
                            if vd.type == "variable_declarator":
                                local_types[txt(field(vd, "name"))] = lt
                for n in walk(body):
                    if n.type != "method_invocation":
                        continue
                    obj = field(n, "object")
                    member = txt(field(n, "name"))
                    owner, resolved, conf = None, False, 0.3
                    if obj is None:
                        owner, resolved, conf = cname, True, 0.8
                    elif obj.type == "this":
                        owner, resolved, conf = cname, True, 0.8
                    elif obj.type == "identifier":
                        q = txt(obj)
                        if q in local_types:
                            owner, resolved, conf = local_types[q], True, 0.7
                        elif q in field_types:
                            owner, resolved, conf = field_types[q], True, 0.7
                        elif q and q[0].isupper():
                            owner, resolved, conf = q, True, 0.6   # static call on a type
                        else:
                            owner, resolved, conf = q, False, 0.3
                    else:
                        owner, resolved, conf = txt(obj), False, 0.3  # complex receiver
                    fqn = imports.get(owner, owner) if owner else None
                    edges.append({"caller": caller,
                                  "callee": {"owner": owner, "owner_fqn": fqn,
                                             "method": member, "qualifier": txt(obj) if obj else ""},
                                  "resolved": resolved, "confidence": conf})
    return {"ok": True, "capability": "build_call_graph", "parser": "tree-sitter-java",
            "resolution": "heuristic-name-type", "root": root, "edges": edges,
            "parse_errors": errors,
            "counts": {"edges": len(edges),
                       "unresolved": sum(1 for e in edges if not e["resolved"]),
                       "files_with_syntax_errors": incomplete,
                       "errors": len(errors)}}


def find_entrypoints(root):
    parser = make_parser()
    hits, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_file(parser, path)
        if err:
            errors.append(err); continue
        pkg, _ = file_package_imports(tree.root_node)
        for cls in (n for n in walk(tree.root_node) if n.type in TYPE_KINDS):
            cname = type_name(cls)
            cls_annos = set(annotations(cls))
            implements = set(implemented_interfaces(cls))
            for m in methods_of(cls):
                m_annos = set(annotations(m))
                mods = set(modifier_keywords(m))
                surfaces = (cls_annos | m_annos) & ENTRYPOINT_ANNOTATIONS
                mname = txt(field(m, "name"))
                is_main = (mname == "main" and "static" in mods and "public" in mods)
                is_runner = (mname == "run" and "CommandLineRunner" in implements)
                if surfaces or is_main or is_runner:
                    hits.append({"file": path,
                                 "type": f"{pkg}.{cname}" if pkg else cname,
                                 "method": mname, "surfaces": sorted(surfaces),
                                 "main": is_main, "runner": is_runner,
                                 "class_annotations": sorted(cls_annos)})
    return {"ok": True, "capability": "discover_entrypoints", "parser": "tree-sitter-java",
            "root": root, "entrypoints": hits, "parse_errors": errors,
            "counts": {"entrypoints": len(hits), "errors": len(errors)}}


def main():
    ap = argparse.ArgumentParser(description="java-maven Tier-2 source analysis (tree-sitter)")
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
