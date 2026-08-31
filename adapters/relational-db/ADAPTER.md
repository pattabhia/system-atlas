# Adapter — relational-db

**Kind:** data store (cross-cutting)
**Binds when:** a boundary of kind *relational database* is reached during traversal (a JDBC/ORM call, a stored-procedure invocation, a SQL string). Bound **by boundary kind**, not by the calling profile's language.
**Prerequisites:** a client for the engine (`psql` / `sqlplus` / `sqlcmd` / `mysql`) **and** read access/credentials to the schema, or offline access to DDL/migration scripts. If neither is available, return `unsupported` with an access boundary gap — do not guess schema.

Implements **`inspect_datastore`** only. Its job: turn a data-store boundary into inspectable evidence, and resolve the semantics of persisted values (codes, statuses, flags) that Skill 06 asks about.

Emit results per the [Adapter Output Contract](../../.claude/skills/shared/stack-adapter-contract.md#adapter-output-contract).

---

## inspect_datastore — Tier 1

### 1. Live introspection (preferred — authoritative, L3)
**PostgreSQL** — run the bundled reference queries:
```bash
psql "$DB_URL" -f scripts/postgres_introspect.sql
```
It dumps tables + columns + types + nullability, primary/foreign keys, views (`pg_get_viewdef`), functions/procedures (`pg_get_functiondef`), and triggers (`pg_get_triggerdef`).

**Oracle** (equivalent objects): `ALL_TAB_COLUMNS`, `ALL_CONSTRAINTS`/`ALL_CONS_COLUMNS`, `ALL_VIEWS.text`, `DBMS_METADATA.GET_DDL('PROCEDURE'|'FUNCTION'|'TRIGGER', name)`, `ALL_SOURCE`.
**SQL Server:** `INFORMATION_SCHEMA.*`, `sys.foreign_keys`, `OBJECT_DEFINITION(OBJECT_ID(name))` for views/procs/triggers.
**MySQL/MariaDB:** `information_schema.*`, `SHOW CREATE TABLE|VIEW|PROCEDURE|FUNCTION|TRIGGER`.

### 2. Offline / no-access fallback (contract only, L2)
If there is no DB connection, run the bundled DDL analyzer over the repo's SQL:
```bash
python3 scripts/ddl_analyze.py <db-scripts-dir> [<upgrade-scripts-dir> ...] > datastore.json
```
It extracts tables/columns/types, and **turns constraints into behavior facts** — `NOT NULL`/PK → required, `DEFAULT` → default behavior, `varchar(n)` → length limit, FK → referential rule, CHECK → validation rule — plus any triggers/functions/procedures/views. Constraints **are behavior** (the DB enforces them regardless of app code); emit them as data-store rules. Mark objects **L2 (contract)**; live reference-data state stays unverified.

**Absence is a finding:** when no triggers/procedures/functions/views exist, the analyzer says so explicitly (`notes`) — record "data-store logic is declarative-only", never leave it silent/un-inspected.

### 3. Semantic / value resolution (feeds Skill 06)
When traversal produced an unresolved persisted value (e.g. a status code written to a column), resolve it here:
- Look up **reference/lookup tables** the column FKs to, and read the row:
  ```sql
  SELECT * FROM <lookup_table> WHERE <code_col> = <value>;
  ```
- Search **check constraints**, **enums** (`pg_enum`), and column comments for allowed values/meaning.
- Trace **triggers and stored procedures** that fire on the affected table — they often carry the real effect.
Report each resolution with its evidence level: value present in reference data + FK → **L3 AUTHORITATIVE**; inferred from a name/comment → **L1 INFERRED**; nothing found → leave `? UNKNOWN`, never invent meaning.

---

## Outputs
`datastore-model.yaml` (tables/columns/keys/views/routines/triggers with provenance); value/semantic resolutions with evidence level; discovered next targets (routines that call other objects, cross-schema/db references); explicit access/version/unresolved gaps.

## Guardrails
- No connection and no DDL in-repo → `✗ MISSING` / access boundary gap, not a guess.
- Stored-procedure/trigger bodies are behavior — hand discovered downstream object references back to the traversal queue.
- Never fabricate reference-data meaning; unknown code semantics stay `? UNKNOWN`.
