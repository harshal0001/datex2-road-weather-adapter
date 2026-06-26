"""Extract the real physical sensor stations (with coordinates) from the raw
*_full_export.csv files into a small committed file the dashboard can draw.

The aggregated/segment-keyed pipeline drops station identity; the full exports keep
it. This pulls the DISTINCT stations + their latest reading per source:

  SWS  →  station_id (P0xx) + lat/lon            (the in-road condition sensors)
  LoRaWAN → deviceName + coords (parsed/columns)
  DWD  →  station_id + lat/lon
  OWM  →  city + lat/lon

Output:  data/sensors.json   (committed — tiny, ~180 points)

Run:  .venv/bin/python scripts/build_sensors.py --downloads "/mnt/e/Ice Prediction"
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sensors.json"

FILES = {
    "sws": "swsweatherreports_full_export.csv",
    "lorawan": "lorawanglatteisv3_full_export.csv",
    "dwd": "dwdclimateweatherhourly_full_export.csv",
    "openweather": "openweathermaphofv1_full_export.csv",
}
_DEVNAME_COORDS = re.compile(r"N(-?\d+\.\d+)-E(-?\d+\.\d+)")


def _clean(v):
    return None if (v is None or v != v) else v   # NaN/None → None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", type=Path, default=Path("/mnt/e/Ice Prediction"))
    args = ap.parse_args()
    base = args.downloads

    import duckdb

    d = duckdb.connect()
    d.execute("PRAGMA threads=4")
    sensors: list[dict] = []
    counts: dict[str, int] = {}

    def latest_per(path, part_col, cols):
        """Latest row per station (cols incl. partition/coord/reading fields)."""
        sel = ", ".join(f'"{c}"' for c in cols)
        q = f"""
            SELECT {sel} FROM read_csv_auto('{path}')
            QUALIFY row_number() OVER (PARTITION BY "{part_col}"
                                       ORDER BY "event_timestamp" DESC) = 1
        """
        return d.execute(q).fetchall()

    # ---- SWS: 13 in-road road-weather stations ----
    p = base / FILES["sws"]
    if p.exists():
        for sid, lat, lon, code, st, at, hum in latest_per(
            p, "station_id",
            ["station_id", "latitude", "longitude", "road_condition_code",
             "road_surface_temperature_celsius", "air_temperature_celsius",
             "relative_humidity_percent"],
        ):
            if lat is None or lon is None:
                continue
            sensors.append({"source": "sws", "id": sid, "name": sid,
                            "lat": float(lat), "lon": float(lon),
                            "reading": {"condition_code": _clean(code),
                                        "surface_temp_c": _clean(st),
                                        "air_temp_c": _clean(at),
                                        "humidity_pct": _clean(hum)}})
        counts["sws"] = sum(s["source"] == "sws" for s in sensors)

    # ---- LoRaWAN: 137 IoT devices (coords parsed from deviceName, fallback columns) ----
    p = base / FILES["lorawan"]
    if p.exists():
        n0 = len(sensors)
        for name, lat, lon, st, at, hum in latest_per(
            p, "deviceName",
            ["deviceName", "lat", "lon", "surface_temperature",
             "air_temperature", "air_humidity"],
        ):
            if not name:
                continue
            m = _DEVNAME_COORDS.search(str(name))
            la, lo = (float(m.group(1)), float(m.group(2))) if m else (_clean(lat), _clean(lon))
            if la is None or lo is None:
                continue
            sensors.append({"source": "lorawan", "id": name, "name": str(name).split("-N")[0],
                            "lat": float(la), "lon": float(lo),
                            "reading": {"surface_temp_c": _clean(st),
                                        "air_temp_c": _clean(at),
                                        "humidity_pct": _clean(hum)}})
        counts["lorawan"] = len(sensors) - n0

    # ---- DWD: the Hof climate station ----
    p = base / FILES["dwd"]
    if p.exists():
        n0 = len(sensors)
        for sid, lat, lon, at, hum, ok in latest_per(
            p, "station_id",
            ["station_id", "latitude", "longitude", "air_temperature_celsius",
             "relative_humidity_percent", "cloud_cover_oktas"],
        ):
            if lat is None or lon is None:
                continue
            sensors.append({"source": "dwd", "id": str(sid), "name": f"DWD {sid}",
                            "lat": float(lat), "lon": float(lon),
                            "reading": {"air_temp_c": _clean(at),
                                        "humidity_pct": _clean(hum),
                                        "cloud_oktas": _clean(ok)}})
        counts["dwd"] = len(sensors) - n0

    # ---- OpenWeather: 26 city points ----
    p = base / FILES["openweather"]
    if p.exists():
        n0 = len(sensors)
        for city, lat, lon, temp, hum, cl in latest_per(
            p, "city",
            ["city", "lat", "lon", "temp", "humidity", "clouds"],
        ):
            if lat is None or lon is None:
                continue
            t = _clean(temp)
            sensors.append({"source": "openweather", "id": str(city), "name": str(city),
                            "lat": float(lat), "lon": float(lon),
                            "reading": {"air_temp_c": (round(t - 273.15, 1) if t is not None else None),
                                        "humidity_pct": _clean(hum),
                                        "clouds_pct": _clean(cl)}})
        counts["openweather"] = len(sensors) - n0

    OUT.write_text(json.dumps({"counts": counts, "sensors": sensors}, indent=1), encoding="utf-8")
    print(f"Done → {OUT}")
    print("  counts:", counts, "· total", len(sensors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
