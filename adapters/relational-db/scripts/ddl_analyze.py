#!/usr/bin/env python3
"""
ddl_analyze.py — extract DB-artifact BEHAVIOR from SQL DDL (offline mode of the
relational-db adapter's inspect_datastore). Free/OSS, no DB connection required.

Parses CREATE TABLE / TRIGGER / FUNCTION / PROCEDURE / VIEW and column constraints
from .sql files, and turns constraints into behavior-relevant facts:
  NOT NULL -> required field; DEFAULT -> default behavior; PK -> identity/uniqueness;
  FK -> referential rule; CHECK -> validation rule; varchar(n) -> length limit.
Reports program objects (trigger/function/procedure/view) that carry logic — and
EXPLICITLY reports when none are found (absence is a finding, not silence).

Usage: ddl_analyze.py <dir-or-file> [<dir-or-file> ...]
Note: heuristic regex parser for common PostgreSQL/ANSI DDL. For authoritative
extraction use the live-introspection path (postgres_introspect.sql).
"""
import json, os, re, sys

def iter_sql(paths):
    for p in paths:
        if os.path.isfile(p) and p.endswith(".sql"):
            yield p
        elif os.path.isdir(p):
            for dp, dn, fn in os.walk(p):
                for f in fn:
                    if f.endswith(".sql"):
                        yield os.path.join(dp, f)

def strip_comments(sql):
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", "", sql)
    return sql

# constraint keywords that terminate the (possibly multi-word) column type
_CONSTRAINT_KW = re.compile(r"\b(not\s+null|null|default|primary\s+key|references|unique|check|constraint)\b", re.I)

def parse_columns(body):
    cols, tbl_constraints = [], []
    depth, cur = 0, ""
    parts = []
    for ch in body:
        if ch == "(":
            depth += 1; cur += ch
        elif ch == ")":
            depth -= 1; cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    for raw in parts:
        s = raw.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith(("constraint", "primary key", "foreign key", "unique", "check")):
            tbl_constraints.append(" ".join(s.split()))
            continue
        parts_ws = s.split(None, 1)
        if len(parts_ws) < 2:
            continue
        name, remainder = parts_ws[0].replace('"', ""), parts_ws[1]
        # type = text up to the first constraint keyword (handles "character varying(36)")
        km = _CONSTRAINT_KW.search(remainder)
        ctype = " ".join((remainder[:km.start()] if km else remainder).split())
        rest = remainder[km.start():] if km else ""
        rl = rest.lower()
        col = {"name": name, "type": ctype,
               "not_null": "not null" in rl,
               "primary_key": "primary key" in rl}
        dm = re.search(r"default\s+([^,]+?)(?:\s+not\s+null|\s+primary\s+key|$)", rest, re.I)
        if dm:
            col["default"] = dm.group(1).strip()
        lm = re.search(r"\(\s*(\d+)\s*\)", ctype)
        if lm:
            col["max_length"] = int(lm.group(1))
        cols.append(col)
    return cols, tbl_constraints

def main():
    paths = sys.argv[1:] or ["."]
    tables, triggers, functions, procedures, views, comments = [], [], [], [], [], []
    files = list(iter_sql(paths))
    for path in files:
        try:
            sql = strip_comments(open(path, encoding="utf-8", errors="replace").read())
        except Exception:
            continue
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)\s*\((.*?)\)\s*;",
                             sql, re.I | re.S):
            name = m.group(1).replace('"', "")
            cols, cons = parse_columns(m.group(2))
            tables.append({"table": name, "file": path, "columns": cols, "table_constraints": cons})
        for kw, bucket in (("trigger", triggers), ("function", functions),
                           ("procedure", procedures), ("view", views)):
            for m in re.finditer(rf"create\s+(?:or\s+replace\s+)?{kw}\s+([\w.\"]+)", sql, re.I):
                # best-effort body capture: prefer $$-delimited, else up to next ';'
                tail = sql[m.end():]
                dd = re.search(r"\$\$(.*?)\$\$", tail, re.S)
                if dd:
                    body = dd.group(1).strip()
                else:
                    body = tail.split(";", 1)[0].strip()
                bucket.append({kw: m.group(1).replace('"', ""), "file": path,
                               "body": body[:4000],
                               "behavior_relevant": True,
                               "note": "program object body — traverse as reachable data-store logic (Skill 05->04)"})
    # behavior facts from constraints
    facts = []
    for t in tables:
        for c in t["columns"]:
            if c.get("not_null") or c.get("primary_key"):
                facts.append({"rule": "required", "table": t["table"], "column": c["name"],
                              "why": "NOT NULL / PK — value must be present"})
            if "default" in c:
                facts.append({"rule": "default", "table": t["table"], "column": c["name"],
                              "value": c["default"], "why": "DB supplies this when unset"})
            if "max_length" in c:
                facts.append({"rule": "length-limit", "table": t["table"], "column": c["name"],
                              "max": c["max_length"], "why": "values truncated/rejected beyond this"})
        for con in t["table_constraints"]:
            kind = ("check" if con.lower().startswith("check") or " check" in con.lower()
                    else "foreign-key" if "foreign key" in con.lower() or "references" in con.lower()
                    else "primary-key" if "primary key" in con.lower()
                    else "unique" if con.lower().startswith("unique") else "constraint")
            facts.append({"rule": kind, "table": t["table"], "definition": con,
                          "why": "enforced by the database"})
    program_objects = len(triggers) + len(functions) + len(procedures) + len(views)
    out = {"ok": True, "capability": "inspect_datastore", "mode": "offline-DDL",
           "files": files, "tables": tables,
           "program_objects": {"triggers": triggers, "functions": functions,
                               "procedures": procedures, "views": views},
           "behavior_facts": facts,
           "counts": {"tables": len(tables), "columns": sum(len(t["columns"]) for t in tables),
                      "triggers": len(triggers), "functions": len(functions),
                      "procedures": len(procedures), "views": len(views),
                      "behavior_facts": len(facts)},
           "notes": ([] if program_objects else
                     ["No triggers/functions/procedures/views found in the DDL — data-store logic "
                      "is limited to declarative constraints. (Explicit absence, not un-inspected.)"])}
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
