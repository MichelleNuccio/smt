from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from skyfield.api import EarthSatellite, load, wgs84

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ORIGINAL_DIR = DATA_DIR / "Original"
PROCESSED_DIR = DATA_DIR / "Processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CITY_CONFIG = {
    "New York": {
        "lat": 40.7128,
        "lon": -74.0060,
        "alt_m": 10.0,
        "tz": "America/New_York",
    },
    "Milan": {
        "lat": 45.4642,
        "lon": 9.19,
        "alt_m": 120.0,
        "tz": "Europe/Rome",
    },
}

HISTORICAL_DATES = [
    "2019-06-15",
    "2019-11-15",
    "2019-11-20",
    "2019-12-01",
]
HISTORICAL_TIMES = [
    "00:00",
    "04:00",
    "08:00",
    "12:00",
    "16:00",
    "20:00",
]
CURRENT_DATE = "2026-10-07"
CURRENT_TIME = "20:00"
DEFAULT_DURATION_MINUTES = 120
SAMPLE_STEP_SECONDS = 15
MAX_ELEMENT_AGE_HOURS = 24
FIRST_CONSTELLATION_LAUNCH = datetime(2019, 5, 24, tzinfo=timezone.utc)


def read_satcat(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as source:
        rows = [
            [cell.strip() for cell in row]
            for row in csv.reader(source, delimiter="\t")
            if row and row[0].strip()
        ]
    if not rows:
        return []
    header = rows[0]
    records = []
    for row in rows[1:]:
        if row and row[0].startswith("#"):
            continue
        row += [""] * max(0, len(header) - len(row))
        records.append(dict(zip(header, row)))
    return records


def parse_satcat_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y %b %d", "%Y %b  %d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def starlink_satellites(records: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    satellites = {}
    for record in records:
        name = (record.get("Name") or "").strip()
        combined_name = f"{name} {(record.get('PLName') or '').strip()}".upper()
        if "STARLINK" not in combined_name or (record.get("Type") or "").strip().startswith("C"):
            continue
        if any(token in combined_name for token in ("PROTOTYPE", "MICROSAT", "DEMO", "TEST", "ROCKET BODY", "DEBRIS", "DEPLOYMENT RAIL")):
            continue
        launch = parse_satcat_date(record.get("LDate") or "")
        if launch is None or launch < FIRST_CONSTELLATION_LAUNCH:
            continue
        norad = (record.get("Satcat") or "").strip()
        if not norad:
            continue
        satellites[norad] = {
            "norad": norad,
            "name": name or (record.get("PLName") or "").strip(),
            "launch_date": launch.date().isoformat(),
        }
    return satellites


def parse_tle_epoch(line1: str) -> datetime:
    epoch_field = line1[18:32]
    year_part = int(epoch_field[:2])
    year = 2000 + year_part if year_part < 57 else 1900 + year_part
    day_of_year = float(epoch_field[2:])
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)


def load_historical_tles(
    path: Path, eligible_ids: set[str]
) -> tuple[list[dict], int, int]:
    lines = path.read_text(encoding="ascii").splitlines()
    records = []
    invalid_pairs = 0
    unmatched_pairs = 0
    if len(lines) % 2:
        invalid_pairs += 1

    for line1, line2 in zip(lines[::2], lines[1::2]):
        first = line1.strip()
        second = line2.strip()
        if not (
            first.startswith("1 ")
            and second.startswith("2 ")
            and first[2:7].isdigit()
            and first[2:7] == second[2:7]
        ):
            invalid_pairs += 1
            continue
        norad = first[2:7]
        if norad not in eligible_ids:
            unmatched_pairs += 1
            continue
        try:
            epoch = parse_tle_epoch(first)
        except ValueError:
            invalid_pairs += 1
            continue
        records.append(
            {
                "norad": norad,
                "line1": first,
                "line2": second,
                "epoch": epoch,
            }
        )
    return records, invalid_pairs, unmatched_pairs


def parse_omm_epoch(value: str) -> datetime:
    epoch = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=timezone.utc)
    return epoch.astimezone(timezone.utc)


def to_utc_from_local(date_iso: str, time_local: str, city_name: str) -> datetime:
    city_tz = ZoneInfo(CITY_CONFIG[city_name]["tz"])
    local_dt = datetime.strptime(
        f"{date_iso} {time_local}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=city_tz)
    return local_dt.astimezone(timezone.utc)


def project_az_el_to_xy(
    az_deg: float, elev_deg: float, radius: float = 240.0
) -> list[float]:
    az_rad = math.radians(az_deg)
    zenith_angle = math.radians(90.0 - elev_deg)
    radial_distance = radius * zenith_angle / math.radians(90.0)
    return [
        radial_distance * math.sin(az_rad),
        -radial_distance * math.cos(az_rad),
    ]


def choose_historical_elements(
    records: list[dict],
    satellites: dict[str, dict[str, str]],
    exposure_start: datetime,
) -> list[dict]:
    newest_by_satellite: dict[str, dict] = {}
    for record in records:
        satellite = satellites[record["norad"]]
        if satellite["launch_date"] > exposure_start.date().isoformat():
            continue
        if record["epoch"] > exposure_start:
            continue
        age_hours = (exposure_start - record["epoch"]).total_seconds() / 3600
        if age_hours > MAX_ELEMENT_AGE_HOURS:
            continue
        previous = newest_by_satellite.get(record["norad"])
        if previous is None or record["epoch"] > previous["epoch"]:
            newest_by_satellite[record["norad"]] = record
    return list(newest_by_satellite.values())


def choose_gp_elements(
    records: list[dict],
    satellites: dict[str, dict[str, str]],
    exposure_start: datetime,
) -> list[dict]:
    selected = []
    for record in records:
        norad = str(record.get("NORAD_CAT_ID", ""))
        satellite = satellites.get(norad)
        if satellite is None or satellite["launch_date"] > exposure_start.date().isoformat():
            continue
        epoch = parse_omm_epoch(str(record["EPOCH"]))
        age_hours = abs((exposure_start - epoch).total_seconds()) / 3600
        if age_hours > MAX_ELEMENT_AGE_HOURS:
            continue
        selected.append(
            {
                "norad": int(norad),
                "name": satellite["name"] or str(record.get("OBJECT_NAME", norad)),
                "omm": record,
                "epoch": epoch,
            }
        )
    return selected


def build_exposure(
    city_name: str,
    date_iso: str,
    time_local: str,
    duration_minutes: int,
    orbital_records: list[dict],
    eligible_satellite_count: int,
    source: str,
    timescale,
) -> dict:
    city = CITY_CONFIG[city_name]
    observer = wgs84.latlon(city["lat"], city["lon"], city["alt_m"])
    start_utc = to_utc_from_local(date_iso, time_local, city_name)
    end_utc = start_utc + timedelta(minutes=duration_minutes)
    segments = []
    calculation_errors = 0
    sample_seconds = list(
        range(0, duration_minutes * 60 + 1, SAMPLE_STEP_SECONDS)
    )
    instants = [start_utc + timedelta(seconds=second) for second in sample_seconds]
    sample_times = timescale.utc(
        [instant.year for instant in instants],
        [instant.month for instant in instants],
        [instant.day for instant in instants],
        [instant.hour for instant in instants],
        [instant.minute for instant in instants],
        [instant.second for instant in instants],
    )
    element_ages = [
        abs((start_utc - record["epoch"]).total_seconds()) / 3600
        for record in orbital_records
    ]

    for record in orbital_records:
        try:
            if "omm" in record:
                satellite = EarthSatellite.from_omm(timescale, record["omm"])
                norad = record["norad"]
                name = record["name"]
            else:
                satellite = EarthSatellite(record["line1"], record["line2"])
                norad = int(record["norad"])
                name = record["name"]
        except (KeyError, TypeError, ValueError):
            calculation_errors += 1
            continue

        points = []
        try:
            topocentric = (satellite - observer).at(sample_times)
            altitude, azimuth, _ = topocentric.altaz()
        except (ValueError, OverflowError, ZeroDivisionError):
            calculation_errors += 1
            continue

        for second, elevation_value, azimuth_value in zip(
            sample_seconds, altitude.degrees, azimuth.degrees
        ):
            elevation = float(elevation_value)
            azimuth_degrees = float(azimuth_value)
            if not (math.isfinite(elevation) and math.isfinite(azimuth_degrees)):
                if len(points) >= 2:
                    segments.append({"norad": norad, "name": name, "points": points})
                points = []
                calculation_errors += 1
                continue

            if elevation > 0:
                xy = project_az_el_to_xy(azimuth_degrees, elevation)
                points.append([xy[0], xy[1], second])
            elif len(points) >= 2:
                segments.append({"norad": norad, "name": name, "points": points})
                points = []

        if len(points) >= 2:
            segments.append({"norad": norad, "name": name, "points": points})

    return {
        "city": city_name,
        "date": date_iso,
        "local_start": time_local,
        "timezone": city["tz"],
        "utc_start": start_utc.isoformat(),
        "utc_end": end_utc.isoformat(),
        "duration_minutes": duration_minutes,
        "eligible_catalog_satellites": eligible_satellite_count,
        "orbital_elements_used": len(orbital_records),
        "max_element_age_hours": max(element_ages, default=0.0),
        "calculation_errors": calculation_errors,
        "segments": segments,
        "source": source,
    }


def main() -> None:
    satcat_path = ORIGINAL_DIR / "satcat.tsv"
    gp_path = ORIGINAL_DIR / "starlink_gp.json"
    historical_path = DATA_DIR / "processed" / "starlink_2019.tle"
    for source_path in (satcat_path, gp_path, historical_path):
        if not source_path.exists():
            raise FileNotFoundError(f"Missing required input: {source_path}")

    satcat_records = read_satcat(satcat_path)
    satellites = starlink_satellites(satcat_records)
    eligible_ids = set(satellites)
    historical_records, invalid_historical_pairs, unmatched_historical_pairs = (
        load_historical_tles(historical_path, eligible_ids)
    )
    for record in historical_records:
        record["name"] = satellites[record["norad"]]["name"]
    gp_records = json.loads(gp_path.read_text(encoding="utf-8"))
    matching_gp_records = [
        record
        for record in gp_records
        if str(record.get("NORAD_CAT_ID", "")) in eligible_ids
    ]

    print(f"Step 1 — satcat rows: {len(satcat_records)}")
    print(f"Step 2 — eligible Starlink payloads: {len(satellites)}")
    print(
        "Step 3 — historical TLE pairs matched: "
        f"{len(historical_records)}; unmatched pairs: "
        f"{unmatched_historical_pairs}; invalid pairs: {invalid_historical_pairs}"
    )
    print(
        f"Step 4 — current GP rows matched: {len(matching_gp_records)} "
        f"of {len(gp_records)}"
    )

    timescale = load.timescale()
    exposures = []
    for city_name in CITY_CONFIG:
        for date_iso in HISTORICAL_DATES:
            for time_local in HISTORICAL_TIMES:
                start_utc = to_utc_from_local(date_iso, time_local, city_name)
                selected = choose_historical_elements(
                    historical_records, satellites, start_utc
                )
                exposures.append(
                    build_exposure(
                        city_name,
                        date_iso,
                        time_local,
                        DEFAULT_DURATION_MINUTES,
                        selected,
                        sum(
                            satellite["launch_date"] <= date_iso
                            for satellite in satellites.values()
                        ),
                        "historical_2019_tle_archive",
                        timescale,
                    )
                )

        start_utc = to_utc_from_local(CURRENT_DATE, CURRENT_TIME, city_name)
        selected_gp = choose_gp_elements(
            matching_gp_records, satellites, start_utc
        )
        exposures.append(
            build_exposure(
                city_name,
                CURRENT_DATE,
                CURRENT_TIME,
                DEFAULT_DURATION_MINUTES,
                selected_gp,
                sum(
                    satellite["launch_date"] <= CURRENT_DATE
                    for satellite in satellites.values()
                ),
                "celestrak_gp_snapshot",
                timescale,
            )
        )

    for exposure in exposures:
        exposure["orbital_coverage"] = (
            "missing"
            if exposure["orbital_elements_used"] == 0
            else "partial"
            if exposure["orbital_elements_used"]
            < exposure["eligible_catalog_satellites"]
            else "complete"
        )
        exposure["coverage"] = (
            "missing_orbital_data"
            if exposure["orbital_elements_used"] == 0
            else "passes"
            if exposure["segments"]
            else "no_passes"
        )
        print(
            f"Step 5 — {exposure['city']} {exposure['date']} "
            f"{exposure['local_start']}: "
            f"{exposure['orbital_elements_used']} elements, "
            f"{len(exposure['segments'])} segments, "
            f"{exposure['coverage']}"
        )

    manifest = {
        "title": "Tracing the sky",
        "version": 2,
        "default_city": "New York",
        "default_date": CURRENT_DATE,
        "default_time": CURRENT_TIME,
        "default_duration_minutes": DEFAULT_DURATION_MINUTES,
        "city_coordinates": CITY_CONFIG,
        "sampling_step_seconds": SAMPLE_STEP_SECONDS,
        "max_orbital_age_hours": MAX_ELEMENT_AGE_HOURS,
        "data_notes": [
            "Only exact city/date/start-time/duration combinations in exposures are supported by this offline build.",
            "No fallback exposure is shown when the selected combination is unsupported.",
            "Elements more than 24 hours from the exposure start are omitted; this is a modeling cutoff, not a positional-accuracy guarantee.",
            "Historical dates use the latest available 2019 TLE at or before the exposure start, matched by NORAD catalog identifier.",
            "The 2026 exposure uses the supplied CelesTrak GP snapshot, matched by NORAD catalog identifier and filtered to elements within 24 hours of the exposure start.",
            "Only catalogued Starlink payloads launched by the exposure date are included; deployment rails, prototypes, debris and rocket bodies are excluded.",
        ],
        "headers": {
            "citations": [
                "CelesTrak Starlink GP elements, downloaded 2026-10-08 UTC.",
                "Space-Track historical TLE archive for 2019, through the supplied Starlink extraction.",
                "satcat.tsv supplied with the assignment for identifiers, object type, names and launch dates.",
                "New York and Milan coordinates are representative city points; no browser geolocation is used.",
            ],
            "limitations": [
                "Predicted orbital elements do not guarantee visible photographic streaks.",
                "Orbital records older than 24 hours relative to an exposure start are excluded by a modeling assumption.",
                "The page only supports exposure presets present in its embedded manifest; unsupported choices show no traces.",
                "Sunlight, brightness, clouds, buildings and camera sensitivity are not modeled.",
            ],
        },
        "exposures": exposures,
        "summary": {
            "satcat_records": len(satcat_records),
            "eligible_starlink_payloads": len(satellites),
            "matched_historical_tle_pairs": len(historical_records),
            "invalid_historical_tle_pairs": invalid_historical_pairs,
            "unmatched_historical_tle_pairs": unmatched_historical_pairs,
            "matched_current_gp_records": len(matching_gp_records),
        },
    }

    serialized = json.dumps(manifest, indent=2)
    for output_name in ("sky_artwork.json", "sky_exposures.json"):
        (PROCESSED_DIR / output_name).write_text(serialized, encoding="utf-8")

    print(
        f"Step 6 — wrote {len(exposures)} supported exposures to "
        f"{PROCESSED_DIR / 'sky_artwork.json'}"
    )


if __name__ == "__main__":
    main()
