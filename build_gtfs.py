#!/usr/bin/env python3
"""Build a one-year static GTFS feed for Turistren. No network requests."""
import argparse
import csv
from datetime import date, timedelta
from io import StringIO
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import holidays

ROOT = Path(__file__).resolve().parent
FIELDS = {
    "agency.txt": ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"],
    "stops.txt": ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"],
    "routes.txt": ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type", "route_url"],
    "trips.txt": ["route_id", "service_id", "trip_id", "trip_headsign", "direction_id", "block_id", "shape_id"],
    "stop_times.txt": ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "pickup_type", "drop_off_type", "timepoint"],
    "calendar.txt": ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"],
    "calendar_dates.txt": ["service_id", "date", "exception_type"],
    "shapes.txt": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
    "feed_info.txt": ["feed_publisher_name", "feed_publisher_url", "feed_lang", "feed_start_date", "feed_end_date", "feed_version"],
}

def csv_text(name, rows):
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS[name], lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()

def shape_rows(path):
    if not path.exists():
        return [], False
    geometry = json.loads(path.read_text(encoding="utf-8"))
    if geometry.get("type") == "FeatureCollection":
        features = geometry["features"]
        if len(features) != 1:
            raise ValueError("Expected one continuous OSM LineString feature")
        geometry = features[0]["geometry"]
    elif geometry.get("type") == "Feature":
        geometry = geometry["geometry"]
    if geometry.get("type") != "LineString":
        raise ValueError("OSM shape must be an ordered single LineString")
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        raise ValueError("Rail shape needs at least two points")
    if any(not (-180 <= lon <= 180 and -90 <= lat <= 90) for lon, lat, *rest in coords):
        raise ValueError("Invalid rail shape coordinate")
    outgoing = [{"shape_id": "SABANA_OUT", "shape_pt_lat": lat, "shape_pt_lon": lon, "shape_pt_sequence": i}
                for i, (lon, lat, *rest) in enumerate(coords, 1)]
    incoming = [{"shape_id": "SABANA_BACK", "shape_pt_lat": lat, "shape_pt_lon": lon, "shape_pt_sequence": i}
                for i, (lon, lat, *rest) in enumerate(reversed(coords), 1)]
    return outgoing + incoming, True

def build(start, end, output, shape_path):
    if start > end:
        raise ValueError("start must be <= end")
    if (end - start).days > 370:
        raise ValueError("Horizon must be at most roughly one year")
    fmt = lambda d: d.strftime("%Y%m%d")
    service_id = "WEEKEND_HOLIDAY"
    shape, has_shape = shape_rows(shape_path)
    data = {
        "agency.txt": [{"agency_id": "TURISTREN", "agency_name": "Turistren",
                        "agency_url": "https://turistren.com.co/", "agency_timezone": "America/Bogota", "agency_lang": "es"}],
        "stops.txt": [
            {"stop_id": "GRAN_ESTACION", "stop_name": "Gran Estación (plataforma férrea)", "stop_lat": 4.648994605275174, "stop_lon": -74.10198771838998, "location_type": 0},
            {"stop_id": "USAQUEN", "stop_name": "Estación de Usaquén", "stop_lat": 4.69063, "stop_lon": -74.03803, "location_type": 0},
            {"stop_id": "ZIPAQUIRA", "stop_name": "Estación de Zipaquirá", "stop_lat": 5.02164, "stop_lon": -74.00115, "location_type": 0},
        ],
        "routes.txt": [{"route_id": "SABANA", "agency_id": "TURISTREN", "route_short_name": "Turistren",
                        "route_long_name": "Bogotá – Usaquén – Zipaquirá", "route_type": 2,
                        "route_url": "https://turistren.com.co/planifica-tu-viaje/"}],
        "trips.txt": [
            {"route_id": "SABANA", "service_id": service_id, "trip_id": "OUTBOUND", "trip_headsign": "Zipaquirá",
             "direction_id": 0, "block_id": "TURISTREN_1", "shape_id": "SABANA_OUT" if has_shape else ""},
            {"route_id": "SABANA", "service_id": service_id, "trip_id": "INBOUND", "trip_headsign": "Gran Estación (Bogotá)",
             "direction_id": 1, "block_id": "TURISTREN_1", "shape_id": "SABANA_BACK" if has_shape else ""},
        ],
        "stop_times.txt": [],
        "calendar.txt": [{"service_id": service_id, "monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0,
                          "friday": 0, "saturday": 1, "sunday": 1, "start_date": fmt(start), "end_date": fmt(end)}],
        "calendar_dates.txt": [],
        "feed_info.txt": [{"feed_publisher_name": "ColombiaTransit", "feed_publisher_url": "https://github.com/ColombiaTransit/gtfs-bogota-turistren",
                           "feed_lang": "es", "feed_start_date": fmt(start), "feed_end_date": fmt(end),
                           "feed_version": f"{fmt(start)}-{fmt(end)}"}],
    }
    # Turistren official website publishes only Usaquén departure (09:15) and return arrival (16:45).
    # The other intermediate timings are provisional, from the ticket partner, pending review.
    for trip, stops in [
        ("OUTBOUND", [("GRAN_ESTACION", "08:45:00", "08:45:00"), ("USAQUEN", "09:05:00", "09:15:00"), ("ZIPAQUIRA", "10:45:00", "10:45:00")]),
        ("INBOUND", [("ZIPAQUIRA", "15:15:00", "15:15:00"), ("USAQUEN", "16:45:00", "16:50:00"), ("GRAN_ESTACION", "17:15:00", "17:15:00")]),
    ]:
        for n, (stop, arr, dep) in enumerate(stops, 1):
            data["stop_times.txt"].append({"trip_id": trip, "arrival_time": arr, "departure_time": dep,
                "stop_id": stop, "stop_sequence": n,
                "pickup_type": 1 if n == len(stops) else 0,
                "drop_off_type": 1 if n == 1 else 0, "timepoint": 1})
    colombian_holidays = holidays.country_holidays("CO", years=range(start.year, end.year + 1))
    day = start
    while day <= end:
        if day.weekday() < 5 and day in colombian_holidays:
            data["calendar_dates.txt"].append({"service_id": service_id, "date": fmt(day), "exception_type": 1})
        day += timedelta(days=1)
    if has_shape:
        data["shapes.txt"] = shape
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zf:
        for name, rows in data.items():
            zf.writestr(name, csv_text(name, rows).encode("utf-8-sig"))
    print(f"Wrote {output}: {len(data['calendar_dates.txt'])} weekday public holidays, OSM shape={has_shape}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2026-11-15")
    p.add_argument("--end", default="2027-11-14")
    p.add_argument("--output", type=Path, default=ROOT / "dist/turistren-gtfs.zip")
    p.add_argument("--shape", type=Path, default=ROOT / "data/rail_shape.geojson")
    args = p.parse_args()
    build(date.fromisoformat(args.start), date.fromisoformat(args.end), args.output, args.shape)
