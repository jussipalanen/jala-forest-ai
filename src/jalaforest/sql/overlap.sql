-- Natura 2000 coverage per forest stand, in EPSG:3067 metres.
--
-- * Only Natura polygons whose interior meets the stand interior in two
--   dimensions count (DE-9IM '2********'); polygons that merely touch the
--   stand boundary along an edge or at a point contribute nothing.
-- * Natura polygons are unioned per stand before intersecting, so
--   overlapping sites (e.g. the same area as both SAC and SPA) are counted
--   once.
-- * The result is built into a new table and swapped in, so readers never
--   see a half-built result.
DROP TABLE IF EXISTS stand_natura_overlap_next;

CREATE TABLE stand_natura_overlap_next AS
WITH pairs AS (
    SELECT s.stand_id, n.site_code, n.site_name, n.geom
    FROM forest_stands s
    JOIN natura_sites n
      ON s.geom && n.geom
     AND ST_Relate(s.geom, n.geom, '2********')
),
per_stand AS (
    SELECT stand_id,
           ST_Union(geom) AS natura_geom,
           array_agg(DISTINCT site_code ORDER BY site_code) AS site_codes,
           array_agg(DISTINCT site_name ORDER BY site_name) AS site_names
    FROM pairs
    GROUP BY stand_id
),
areas AS (
    SELECT s.stand_id,
           ST_Area(s.geom) AS stand_area_m2,
           COALESCE(
               ST_Area(ST_CollectionExtract(ST_Intersection(s.geom, p.natura_geom), 3)),
               0
           ) AS overlap_m2,
           COALESCE(p.site_codes, ARRAY[]::text[]) AS natura_site_codes,
           COALESCE(p.site_names, ARRAY[]::text[]) AS natura_site_names,
           s.geom
    FROM forest_stands s
    LEFT JOIN per_stand p USING (stand_id)
)
SELECT stand_id,
       stand_area_m2 / 10000.0 AS stand_area_ha,
       overlap_m2 / 10000.0 AS natura_overlap_ha,
       CASE WHEN stand_area_m2 > 0
            THEN LEAST(100.0, 100.0 * overlap_m2 / stand_area_m2)
            ELSE 0 END AS natura_overlap_pct,
       natura_site_codes,
       natura_site_names,
       geom
FROM areas;

ALTER TABLE stand_natura_overlap_next ADD PRIMARY KEY (stand_id);

DROP TABLE IF EXISTS stand_natura_overlap;
ALTER TABLE stand_natura_overlap_next RENAME TO stand_natura_overlap;
ALTER INDEX stand_natura_overlap_next_pkey RENAME TO stand_natura_overlap_pkey;
