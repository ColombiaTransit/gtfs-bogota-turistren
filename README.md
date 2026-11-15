# Turistren — Tren de la Sabana (unofficial GTFS)

Static GTFS for the Bogotá (Gran Estación) – Usaquén – Zipaquirá tourist train.

## Sources and policy
- Official schedule: https://turistren.com.co/planifica-tu-viaje/
- Operating days: https://turistren.com.co/preguntas-frecuentes/ (Saturday, Sunday, Colombian public holidays).
- Holidays: Python `holidays.country_holidays("CO")`, not a handwritten holiday list.
- Timezone: America/Bogota.
- Source checked: 2026-11-15. Timetable is a public *planning* schedule, not guaranteed operation on each date.
- Validity window: 2026-11-15 through 2027-11-14, inclusive (one year). Revisit website annually, then renew dates.
- Departures: Gran Estación 08:45, Usaquén 09:15, Zipaquirá arrival 10:45. Return: Zipaquirá 15:15, Usaquén arrival 16:45, Gran Estación arrival 17:15. The official itinerary only states Usaquén outbound departure 09:15 and inbound arrival 16:45. The feed uses these values in both arrival/departure fields rather than inventing dwell times.
- Stop coordinates: Gran Estación uses the official Turistren Google Maps coordinates; Usaquén (OSM node 9439042609) and Zipaquirá (OSM node 761227000) use the one-time OSM station export.
- Tren de la Navidad is a separate product and is **excluded**, as are charter trains and buses to Catedral de Sal.
- The official website sells only return tickets; GTFS separately represents the outbound and inbound physical train trips.

## Generate
```bash
python -m pip install -r requirements.txt
python build_gtfs.py --start 2026-11-15 --end 2027-11-14
```
Output: `dist/turistren-gtfs.zip`.

## Geometry
Rail geometry must be extracted from OpenStreetMap **once**, verified and committed as `data/rail_shape.geojson` (LineString ordered Gran Estación -> Usaquén -> Zipaquirá). Both trips reuse the line with reverse ordering for the return. Do not connect arbitrary straight lines or download OSM at every GTFS generation. The static OSM-based geometry has been committed to `data/rail_shape.geojson`; verify the alignment and station proximity before the first release.

## CI and releases
`Build & validate GTFS` runs on push and manual dispatch. It downloads MobilityData GTFS Validator v8.0.1, archives JSON/HTML reports, and fails if ERROR notices or system errors are present. Only manual dispatch with `publish=true` can create a GitHub release, gated on validator success and existence of the committed OSM geometry. The release has `turistren-gtfs.zip`, with a stable latest URL after the first successful release.

`Annual source review` opens a GitHub issue on November 1 each year (no automatic website scraping or schedule changes). Review official times, operation days, special trips, and source status; only then extend the service horizon and publish a validated feed.
