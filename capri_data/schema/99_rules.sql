-- Rules over every declaration (run after all files are loaded): the units of the long tables' numeric columns.
-- A long table's numeric column has one unit, declared in value_units with the column's name as the item. Tables whose
-- units are per item rather than per column (a wide table's `value` column; producer_prices, one unit per activity
-- in a key column) are left to their own file's rules; the validator's own work tables (names from `_`) are skipped.

-- rule: every numeric column of a long table has its unit declared (or is declared open), and every unit is in the catalogue
WITH itemised AS (
    SELECT table_name AS tbl FROM information_schema.columns WHERE column_name = 'value'
    UNION
    SELECT v.tbl FROM value_units v
    WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns c WHERE c.table_name = v.tbl AND c.column_name = v.item))
SELECT c.table_name, c.column_name, 'no unit declared' AS what
FROM information_schema.columns c
WHERE c.data_type IN ('DOUBLE', 'FLOAT', 'DECIMAL', 'INTEGER', 'BIGINT')
  AND c.table_name NOT IN (SELECT tbl FROM itemised)
  AND c.table_name <> 'value_units' AND NOT starts_with(c.table_name, '_')
  AND NOT EXISTS (SELECT 1 FROM value_units v WHERE v.tbl = c.table_name AND v.item = c.column_name)
UNION ALL
SELECT tbl, item, 'unit not in the catalogue' FROM value_units WHERE unit IS NOT NULL AND unit NOT IN (SELECT code FROM units);

-- rule: every table named in value_units is declared
SELECT DISTINCT tbl FROM value_units WHERE tbl NOT IN (SELECT table_name FROM information_schema.tables);
