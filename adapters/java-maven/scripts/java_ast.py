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


def _line(node):
    return node.start_point[0] + 1


def _cond_text(node):
    c = field(node, "condition")
    t = txt(c) if c is not None else ""
    t = " ".join((t or "").split())
    return t[:80]


def build_branches(root):
    """Enumerate branch constructs per method — the behavior-variant subset:
    if / else, switch cases + default, ternary, catch clauses, loops. Each branch
    lists its arms so Skill 04/06 can confirm every arm is represented in the
    decision/behavior model (branch-completeness)."""
    parser = make_parser()
    methods_out, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_file(parser, path)
        if err:
            errors.append(err); continue
        pkg, _ = file_package_imports(tree.root_node)
        for cls in (n for n in walk(tree.root_node) if n.type in TYPE_KINDS):
            cname = type_name(cls)
            for m in methods_of(cls):
                mname = txt(field(m, "name"))
                qual = f"{pkg}.{cname}#{mname}" if pkg else f"{cname}#{mname}"
                body = field(m, "body")
                if body is None:
                    continue
                branches = []
                for n in walk(body):
                    t = n.type
                    if t == "if_statement":
                        has_else = field(n, "alternative") is not None
                        branches.append({"type": "if", "line": _line(n),
                                          "cond": _cond_text(n),
                                          "arms": ["then", "else" if has_else else "implicit-else"]})
                    elif t == "ternary_expression":
                        branches.append({"type": "ternary", "line": _line(n),
                                          "arms": ["then", "else"]})
                    elif t == "switch_expression":
                        cases, has_default = [], False
                        blk = field(n, "body")
                        if blk is not None:
                            for g in blk.children:
                                if g.type in ("switch_block_statement_group", "switch_rule"):
                                    for lab in g.children:
                                        if lab.type == "switch_label":
                                            lt = txt(lab)
                                            if lt and lt.strip().startswith("default"):
                                                has_default = True
                                            else:
                                                cases.append(" ".join((lt or "").split()))
                        arms = cases + (["default"] if has_default else [])
                        branches.append({"type": "switch", "line": _line(n),
                                          "arms": arms or ["(empty)"]})
                    elif t == "catch_clause":
                        # exception type(s) in the catch parameter
                        param = field(n, "parameter") or n
                        et = ""
                        for cc in walk(param):
                            if cc.type in ("catch_type", "type_identifier", "union_type"):
                                et = " ".join((txt(cc) or "").split()); break
                        branches.append({"type": "catch", "line": _line(n),
                                          "arms": [et or "exception"]})
                    elif t in ("while_statement", "do_statement",
                               "for_statement", "enhanced_for_statement"):
                        branches.append({"type": "loop", "line": _line(n),
                                         "cond": _cond_text(n), "arms": ["enter", "skip/exit"]})
                if branches:
                    methods_out.append({"method": qual, "file": path,
                                        "branches": sorted(branches, key=lambda b: b["line"])})
    tot_b = sum(len(m["branches"]) for m in methods_out)
    tot_a = sum(len(b["arms"]) for m in methods_out for b in m["branches"])
    return {"ok": True, "capability": "branch_inventory", "parser": "tree-sitter-java",
            "root": root, "methods": methods_out, "parse_errors": errors,
            "counts": {"methods_with_branches": len(methods_out),
                       "branches": tot_b, "arms": tot_a, "errors": len(errors)}}


def _stmts(block):
    return [c for c in block.children if c.is_named] if block is not None else []


def classify_catch(catch_node):
    """Classify a catch handler's body — the recurring 'silent failure' axis that
    error-handling reconstruction must surface (swallowed exceptions hide behavior)."""
    body = None
    for c in catch_node.children:
        if c.type == "block":
            body = c; break
    if body is None:
        return "unknown", False
    has_throw = has_return_null = has_return_other = has_log = has_other = False
    # inspect only TOP-LEVEL statements of the catch block (not nested arg calls,
    # so a log call whose argument is a method invocation still counts as logging)
    stmts = [c for c in body.children if c.is_named]
    empty = len(stmts) == 0
    for s in stmts:
        t = s.type
        if t == "throw_statement":
            has_throw = True
        elif t == "return_statement":
            rv = " ".join((txt(s) or "").split()).rstrip(";")
            if rv.endswith("null") or rv.endswith("false") or rv.endswith("0") or rv == "return":
                has_return_null = True
            else:
                has_return_other = True
        elif t == "expression_statement":
            inner = next((c for c in s.children if c.is_named), None)
            if inner is not None and inner.type == "method_invocation":
                q = txt(field(inner, "object")) or ""
                mm = (txt(field(inner, "name")) or "").lower()
                if "log" in q.lower() or mm in ("error", "warn", "info", "debug", "trace"):
                    has_log = True
                else:
                    has_other = True
            else:
                has_other = True
        else:  # if/for/try/local-var/assignment doing real recovery work
            has_other = True
    if has_throw:
        return "rethrow-or-wrap", False
    if has_other or has_return_other:
        return "recover-or-other", False
    if has_return_null:
        return "swallow-return-null/false", True
    if empty:
        return "swallow-empty", True
    if has_log:
        return "swallow-log-only", True
    return "swallow-empty", True


def build_exceptions(root):
    """Per-method catch-handler analysis. Flags SILENT-FAILURE handlers (swallow: log-only,
    empty, or return null/false) — a top modernization concern that hides real behavior."""
    parser = make_parser()
    methods_out, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_file(parser, path)
        if err:
            errors.append(err); continue
        pkg, _ = file_package_imports(tree.root_node)
        for cls in (n for n in walk(tree.root_node) if n.type in TYPE_KINDS):
            cname = type_name(cls)
            for m in methods_of(cls):
                mname = txt(field(m, "name"))
                qual = f"{pkg}.{cname}#{mname}" if pkg else f"{cname}#{mname}"
                body = field(m, "body")
                if body is None:
                    continue
                handlers = []
                for n in walk(body):
                    if n.type == "catch_clause":
                        et = ""
                        for cc in walk(field(n, "parameter") or n):
                            if cc.type in ("catch_type", "type_identifier", "union_type"):
                                et = " ".join((txt(cc) or "").split()); break
                        kind, silent = classify_catch(n)
                        handlers.append({"line": _line(n), "exception": et or "?",
                                         "handling": kind, "silent_failure": silent})
                if handlers:
                    methods_out.append({"method": qual, "file": path, "handlers": handlers})
    silent = [(m["method"], h) for m in methods_out for h in m["handlers"] if h["silent_failure"]]
    return {"ok": True, "capability": "exception_analysis", "parser": "tree-sitter-java",
            "root": root, "methods": methods_out, "parse_errors": errors,
            "silent_failures": [{"method": mth, **h} for mth, h in silent],
            "counts": {"methods_with_catches": len(methods_out),
                       "handlers": sum(len(m["handlers"]) for m in methods_out),
                       "silent_failures": len(silent), "errors": len(errors)}}


def build_errorcodes(root):
    """Extract enum constants (error/status/reason codes) with their literal arguments —
    e.g. DigitalCardServiceErrorCodes.PDF_NOT_GENERATED("code","message"). These carry
    domain semantics (Skill 06) and are the values written to status_comment / raised in
    exceptions; catalog them instead of leaving them scattered across catch blocks."""
    parser = make_parser()
    enums, errors = [], []
    for path in iter_java_files(root):
        tree, err = parse_file(parser, path)
        if err:
            errors.append(err); continue
        pkg, _ = file_package_imports(tree.root_node)
        for decl in (n for n in walk(tree.root_node) if n.type == "enum_declaration"):
            ename = type_name(decl)
            body = field(decl, "body")
            if body is None:
                continue
            consts = []
            for ec in (c for c in walk(body) if c.type == "enum_constant"):
                cname = txt(field(ec, "name"))
                args = []
                al = field(ec, "arguments")
                if al is not None:
                    for a in al.children:
                        if a.type in ("string_literal", "decimal_integer_literal",
                                      "character_literal", "true", "false"):
                            v = txt(a)
                            if a.type == "string_literal":
                                v = v[1:-1] if v and len(v) >= 2 else v
                            args.append(v)
                consts.append({"name": cname, "args": args})
            if consts:
                enums.append({"enum": f"{pkg}.{ename}" if pkg else ename,
                              "file": path, "constants": consts})
    return {"ok": True, "capability": "code_catalog", "parser": "tree-sitter-java",
            "root": root, "enums": enums, "parse_errors": errors,
            "counts": {"enums": len(enums),
                       "constants": sum(len(e["constants"]) for e in enums),
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
    g.add_argument("--branches", action="store_true")
    g.add_argument("--exceptions", action="store_true")
    g.add_argument("--errorcodes", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(json.dumps({"ok": False, "error": "root_not_found", "root": args.root}))
        sys.exit(1)

    if args.model:
        result = build_model(args.root)
    elif args.callgraph:
        result = build_callgraph(args.root)
    elif args.branches:
        result = build_branches(args.root)
    elif args.exceptions:
        result = build_exceptions(args.root)
    elif args.errorcodes:
        result = build_errorcodes(args.root)
    else:
        result = find_entrypoints(args.root)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
