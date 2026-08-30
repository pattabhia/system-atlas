-- postgres_introspect.sql — reference introspection for the relational-db adapter.
-- Read-only. Run:  psql "$DB_URL" -f postgres_introspect.sql
-- Restrict to user schemas (skip system + info schemas).

\pset pager off

\echo '== tables & columns =='
SELECT c.table_schema, c.table_name, c.column_name, c.data_type,
       c.is_nullable, c.column_default, c.character_maximum_length
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE t.table_type = 'BASE TABLE'
  AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY c.table_schema, c.table_name, c.ordinal_position;

\echo '== primary & foreign keys =='
SELECT tc.constraint_type, tc.table_schema, tc.table_name, kcu.column_name,
       ccu.table_name AS ref_table, ccu.column_name AS ref_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name AND tc.constraint_type = 'FOREIGN KEY'
WHERE tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY tc.table_schema, tc.table_name, tc.constraint_type;

\echo '== check constraints (allowed-value hints) =='
SELECT tc.table_schema, tc.table_name, cc.constraint_name, cc.check_clause
FROM information_schema.check_constraints cc
JOIN information_schema.table_constraints tc USING (constraint_schema, constraint_name)
WHERE tc.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY tc.table_schema, tc.table_name;

\echo '== enums (allowed values) =='
SELECT n.nspname AS schema, t.typname AS enum_type,
       string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS values
FROM pg_type t
JOIN pg_enum e ON e.enumtypid = t.oid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
GROUP BY 1, 2 ORDER BY 1, 2;

\echo '== view definitions =='
SELECT schemaname, viewname, pg_get_viewdef(format('%I.%I', schemaname, viewname)::regclass, true) AS definition
FROM pg_views
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, viewname;

\echo '== functions & procedures (bodies are behavior) =='
SELECT n.nspname AS schema, p.proname AS name,
       pg_get_function_identity_arguments(p.oid) AS args,
       pg_get_functiondef(p.oid) AS definition
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;

\echo '== triggers =='
SELECT n.nspname AS schema, c.relname AS table, t.tgname AS trigger,
       pg_get_triggerdef(t.oid, true) AS definition
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT t.tgisinternal
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2, 3;
