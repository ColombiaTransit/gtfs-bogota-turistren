# One-time OSM shape

Place a verified GeoJSON LineString at `data/rail_shape.geojson`.

It must follow the actual railway track, ordered Gran Estación -> Usaquén -> Zipaquirá. Use actual OSM railway ways, not a straight-line interpolation. Check track connectivity, platform proximity, and license attribution (OpenStreetMap contributors, ODbL). The generator produces both directional GTFS shape IDs from this static geometry. Do not auto-refetch annually.

This geometry has **not yet been retrieved or verified**. The release workflow refuses to publish without it.
