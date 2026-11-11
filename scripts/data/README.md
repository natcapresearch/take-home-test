# scripts/data

`admin_regions.json` holds the `COUNTRY`-level administrative boundaries for the
15 sourcing countries used by `scripts/seed.py` (AR, AU, BR, CI, CO, ET, FR, GH,
ID, IN, MY, TH, UA, US, VN), with geometry simplified to a 0.05° tolerance.

It is a JSON array of objects with exactly these keys: `uid` (uuid), `name`,
`level` (`COUNTRY` or `REGION`), `country_code` (ISO 3166-1 alpha-2, e.g.
`BR`), `country_name`, `geojson_simplified` (a GeoJSON geometry object, or
`null`). `seed.py` upserts every row (matching on `(level, country_code, name)`,
then on `uid`) and links each commodity source to the `COUNTRY` row of its
sourcing country; a seed country missing from this file still gets its sources,
but they have no geometry on the map.
