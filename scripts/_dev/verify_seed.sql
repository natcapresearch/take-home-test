-- Verify what the versioned reads return for the seeded organisation.
--
-- A raw-SQL port of src/backend/app/util/change_set.py `change_set_query`
-- (lines 300-401 on origin/main), applied the way
-- api/v2/commodity_location.py uses it: entity aliveness from
-- commodity_location_entity, then each alive entity's
-- exported_commodity_location row current as of the change set
-- (util/change_set_export.py `exported_rows_for_changeset_subquery`).
--
-- Run with psql variables:
--   psql ... -v org_uid=<org> -v v1=<version 1 uid> -v v2=<version 2 uid> \
--        -f scripts/_dev/verify_seed.sql

\set ON_ERROR_STOP on

-- One function so the CTE is written once. `winners` is the alive set of
-- `model_type` rows as of `cs_uid`.
CREATE OR REPLACE FUNCTION pg_temp.alive_uids(cs_uid uuid, p_org_uid uuid, model_type text)
RETURNS TABLE (uid uuid) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY EXECUTE format($q$
        WITH RECURSIVE cs_chain AS (
            SELECT cs.uid, cs.parent_uid, 0 AS ordering_number
            FROM change_set cs WHERE cs.uid = $1
            UNION ALL
            SELECT cs.uid, cs.parent_uid, cs_chain.ordering_number + 1
            FROM change_set cs JOIN cs_chain ON cs_chain.parent_uid = cs.uid
        ),
        relevant_changes AS (
            SELECT c.new_uid, c.previous_uid, cs_chain.ordering_number
            FROM change c JOIN cs_chain ON c.change_set_uid = cs_chain.uid
            WHERE c.org_uid = $2 AND c.model_type = $3
        ),
        versions AS (
            SELECT %1$s AS matching, m.uid AS version_uid, m.created_at,
                   rc.ordering_number, rc.new_uid
            FROM relevant_changes rc
            JOIN %2$I m ON m.uid = COALESCE(rc.new_uid, rc.previous_uid)
            WHERE %1$s IS NOT NULL
        ),
        windowed AS (
            SELECT version_uid, created_at, ordering_number, new_uid,
                   MIN(ordering_number) OVER (PARTITION BY matching) AS nearest_ordering_number,
                   MAX(created_at) OVER (PARTITION BY matching) AS latest_created_at
            FROM versions
        )
        SELECT DISTINCT version_uid FROM windowed
        WHERE created_at = latest_created_at
          AND ordering_number = nearest_ordering_number
          AND new_uid = version_uid
    $q$,
        -- __matching_columns__: uid for the entity, entity_uid for the
        -- exported row (exported_commodity_location.py line 181).
        CASE WHEN model_type = 'exported_commodity_location' THEN 'm.entity_uid' ELSE 'm.uid' END,
        model_type)
    USING cs_uid, p_org_uid, model_type;
END $$;

\echo '--- alive entities per version (expect 120 / 121)'
SELECT 'Version 1' AS version, count(*) FROM pg_temp.alive_uids(:'v1', :'org_uid', 'commodity_location_entity')
UNION ALL
SELECT 'Version 2', count(*) FROM pg_temp.alive_uids(:'v2', :'org_uid', 'commodity_location_entity');

\echo '--- exported rows current per version, restricted to alive entities (expect 120 / 121)'
SELECT 'Version 1' AS version, count(*) FROM exported_commodity_location e
WHERE e.uid IN (SELECT uid FROM pg_temp.alive_uids(:'v1', :'org_uid', 'exported_commodity_location'))
  AND e.entity_uid IN (SELECT uid FROM pg_temp.alive_uids(:'v1', :'org_uid', 'commodity_location_entity'))
UNION ALL
SELECT 'Version 2', count(*) FROM exported_commodity_location e
WHERE e.uid IN (SELECT uid FROM pg_temp.alive_uids(:'v2', :'org_uid', 'exported_commodity_location'))
  AND e.entity_uid IN (SELECT uid FROM pg_temp.alive_uids(:'v2', :'org_uid', 'commodity_location_entity'));

\echo '--- exported rows current per version, unrestricted (expect 120 / 121: tombstoned rows are dead too)'
SELECT 'Version 1' AS version, count(*) FROM pg_temp.alive_uids(:'v1', :'org_uid', 'exported_commodity_location')
UNION ALL
SELECT 'Version 2', count(*) FROM pg_temp.alive_uids(:'v2', :'org_uid', 'exported_commodity_location');

\echo '--- rows whose current version differs between V1 and V2 (expect 10 replaced + 2 removed + 3 new)'
WITH v1 AS (
    SELECT e.* FROM exported_commodity_location e
    WHERE e.uid IN (SELECT uid FROM pg_temp.alive_uids(:'v1', :'org_uid', 'exported_commodity_location'))
), v2 AS (
    SELECT e.* FROM exported_commodity_location e
    WHERE e.uid IN (SELECT uid FROM pg_temp.alive_uids(:'v2', :'org_uid', 'exported_commodity_location'))
)
SELECT COALESCE(v1.identifier, v2.identifier) AS identifier,
       CASE WHEN v1.uid IS NULL THEN 'new' WHEN v2.uid IS NULL THEN 'removed' ELSE 'replaced' END AS kind,
       v1.sourcing_country_name AS v1_country, v2.sourcing_country_name AS v2_country,
       v1.supplier AS v1_supplier, v2.supplier AS v2_supplier,
       v1.spend AS v1_spend, v2.spend AS v2_spend,
       v1.quantity_kilograms AS v1_kg, v2.quantity_kilograms AS v2_kg
FROM v1 FULL OUTER JOIN v2 ON v1.entity_uid = v2.entity_uid
WHERE v1.uid IS DISTINCT FROM v2.uid
ORDER BY kind, identifier;

\echo '--- summary figures per version (get_commodity_summary shape)'
WITH alive AS (
    SELECT 'Version 1' AS version, uid FROM pg_temp.alive_uids(:'v1', :'org_uid', 'commodity_location_entity')
    UNION ALL
    SELECT 'Version 2', uid FROM pg_temp.alive_uids(:'v2', :'org_uid', 'commodity_location_entity')
), current_rows AS (
    SELECT 'Version 1' AS version, uid FROM pg_temp.alive_uids(:'v1', :'org_uid', 'exported_commodity_location')
    UNION ALL
    SELECT 'Version 2', uid FROM pg_temp.alive_uids(:'v2', :'org_uid', 'exported_commodity_location')
)
SELECT a.version,
       count(*) AS entities,
       count(DISTINCT e.commodity_subgroup) AS total_commodities,
       count(DISTINCT e.sourcing_country_name) AS total_locations,
       round(sum(e.spend)::numeric) AS total_spend,
       round(sum(e.quantity_kilograms)::numeric) AS total_quantity,
       count(*) FILTER (WHERE e.quantity_kilograms IS NULL) AS missing_quantity,
       count(*) FILTER (WHERE e.spend IS NULL) AS missing_spend,
       count(DISTINCT ce.supplier) AS total_suppliers
FROM alive a
JOIN commodity_location_entity ce ON ce.uid = a.uid
JOIN exported_commodity_location e ON e.entity_uid = a.uid
JOIN current_rows cr ON cr.version = a.version AND cr.uid = e.uid
GROUP BY a.version ORDER BY a.version;

\echo '--- admin_region join (get_aggregated_commodity_regions): one row per sourcing country, V2'
WITH alive AS (
    SELECT uid FROM pg_temp.alive_uids(:'v2', :'org_uid', 'commodity_location_entity')
), current_rows AS (
    SELECT uid FROM pg_temp.alive_uids(:'v2', :'org_uid', 'exported_commodity_location')
)
SELECT COALESCE(ar.country_name, e.sourcing_country_name) AS country,
       e.sourcing_country_code AS code,
       ar.level AS region_level,
       country_region.uid IS NOT NULL AS has_country_geometry,
       count(*) AS sources,
       round(sum(e.spend)::numeric) AS total_spend
FROM exported_commodity_location e
JOIN current_rows cr ON cr.uid = e.uid
JOIN commodity_location_entity ce ON ce.uid = e.entity_uid AND ce.uid IN (SELECT uid FROM alive)
LEFT JOIN admin_region ar ON ar.uid = ce.sourcing_admin_region_uid
LEFT JOIN admin_region country_region
       ON country_region.level = 'COUNTRY' AND country_region.country_code = ar.country_code
GROUP BY 1, 2, 3, 4 ORDER BY 1;

\echo '--- change sets'
SELECT name, state, parent_uid IS NOT NULL AS has_parent, published_at, description, datashape
FROM change_set WHERE org_uid = :'org_uid' ORDER BY created_at;

\echo '--- organisation default change set (expect Version 1)'
SELECT o.name, cs.name AS default_change_set, o.config
FROM organisation o JOIN change_set cs ON cs.uid = o.default_change_set_uid
WHERE o.uid = :'org_uid';
