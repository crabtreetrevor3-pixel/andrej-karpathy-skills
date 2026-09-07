#!/usr/bin/env python3
"""
Score target areas for roof-replacement lead potential using home age and
storm damage history.

Combines two public data sources:
  - Census ACS 5-year estimates: median year structure built, by ZCTA
    (table B25035) - a proxy for roof age.
  - NOAA Storm Events Database: county-level history of hail, thunderstorm
    wind, tornado, and hurricane/tropical storm events - a proxy for storm
    damage exposure.

NOAA's storm data is tracked by county (and sometimes NWS forecast zone),
not zip code, so you provide a small mapping CSV of zip -> county -> state
for your target areas (see areas_template.csv). Home age is looked up
directly by zip via Census.

Usage:
    python roof_lead_finder.py score areas.csv --years 5 --out leads.csv

areas.csv columns: zip,county,state (state as 2-letter USPS abbreviation,
county without the word "County", e.g. "Stone", not "Stone County")
"""
import argparse
import csv
import gzip
import io
import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime

CENSUS_ACS_URL = "https://api.census.gov/data/2022/acs/acs5"
NOAA_INDEX_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
ROOF_DAMAGE_EVENT_TYPES = {
    "hail",
    "thunderstorm wind",
    "tornado",
    "hurricane",
    "hurricane (typhoon)",
    "tropical storm",
    "high wind",
    "strong wind",
}


def fetch_home_age(zip_codes, api_key=None):
    """Return {zip: median_year_structure_built} via ACS ZCTA estimates."""
    params = f"get=NAME,B25035_001E&for=zip%20code%20tabulation%20area:{','.join(zip_codes)}"
    if api_key:
        params += f"&key={api_key}"
    url = f"{CENSUS_ACS_URL}?{params}"
    with urllib.request.urlopen(url) as resp:
        rows = json.loads(resp.read().decode())
    header, data = rows[0], rows[1:]
    zcta_idx = header.index("zip code tabulation area")
    year_idx = header.index("B25035_001E")
    result = {}
    for row in data:
        val = row[year_idx]
        if val not in (None, "null", "-666666666"):
            result[row[zcta_idx]] = int(val)
    return result


def list_noaa_detail_files(year):
    """Find the StormEvents details filename for a given year from NOAA's index."""
    with urllib.request.urlopen(NOAA_INDEX_URL) as resp:
        html = resp.read().decode()
    pattern = rf'StormEvents_details-ftp_v1\.0_d{year}_c\d+\.csv\.gz'
    match = re.search(pattern, html)
    if not match:
        return None
    return NOAA_INDEX_URL + match.group(0)


def fetch_storm_events_for_year(year):
    """Download and parse one year's NOAA storm events detail file."""
    url = list_noaa_detail_files(year)
    if not url:
        print(f"warning: no NOAA storm events file found for {year}", file=sys.stderr)
        return []
    with urllib.request.urlopen(url) as resp:
        raw = gzip.decompress(resp.read())
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")))
    return list(reader)


def count_storm_events(counties, start_year, end_year):
    """counties: set of (state_abbr, county_name_lowercase). Returns {(state, county): count}."""
    counts = defaultdict(int)
    for year in range(start_year, end_year + 1):
        for row in fetch_storm_events_for_year(year):
            event_type = (row.get("EVENT_TYPE") or "").strip().lower()
            if event_type not in ROOF_DAMAGE_EVENT_TYPES:
                continue
            state = (row.get("STATE") or "").strip().lower()
            county = (row.get("CZ_NAME") or "").strip().lower()
            counts[(state, county)] += 1
    # re-key by (STATE_ABBR, county) for lookup against areas.csv
    return counts


STATE_ABBR_TO_NAME = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas", "CA": "california",
    "CO": "colorado", "CT": "connecticut", "DE": "delaware", "FL": "florida", "GA": "georgia",
    "HI": "hawaii", "ID": "idaho", "IL": "illinois", "IN": "indiana", "IA": "iowa",
    "KS": "kansas", "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
    "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada", "NH": "new hampshire",
    "NJ": "new jersey", "NM": "new mexico", "NY": "new york", "NC": "north carolina",
    "ND": "north dakota", "OH": "ohio", "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania",
    "RI": "rhode island", "SC": "south carolina", "SD": "south dakota", "TN": "tennessee",
    "TX": "texas", "UT": "utah", "VT": "vermont", "VA": "virginia", "WA": "washington",
    "WV": "west virginia", "WI": "wisconsin", "WY": "wyoming", "DC": "district of columbia",
}


def cmd_score(args):
    with open(args.areas_csv, newline="", encoding="utf-8-sig") as f:
        areas = list(csv.DictReader(f))
    if not areas:
        sys.exit("areas.csv is empty")

    zips = [a["zip"].strip() for a in areas]
    ages = fetch_home_age(zips, api_key=args.api_key)

    end_year = datetime.now().year - 1  # last fully-recorded year
    start_year = end_year - args.years + 1
    needed_counties = {(a["state"].strip().upper(), a["county"].strip().lower()) for a in areas}
    storm_counts_by_name = count_storm_events(needed_counties, start_year, end_year)

    rows = []
    for a in areas:
        z = a["zip"].strip()
        state_abbr = a["state"].strip().upper()
        county = a["county"].strip().lower()
        state_full = STATE_ABBR_TO_NAME.get(state_abbr, state_abbr.lower())
        storm_count = storm_counts_by_name.get((state_full, county), 0)
        year_built = ages.get(z)
        age_years = (datetime.now().year - year_built) if year_built else None
        rows.append({
            "zip": z,
            "county": a["county"].strip(),
            "state": state_abbr,
            "median_year_built": year_built or "",
            "home_age_years": age_years or "",
            "storm_events_last_%dy" % args.years: storm_count,
            "priority_score": (age_years or 0) + storm_count * args.storm_weight,
        })

    rows.sort(key=lambda r: r["priority_score"], reverse=True)

    fieldnames = list(rows[0].keys())
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} scored areas to {args.out}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="Score zip/county areas by home age + storm damage history")
    p_score.add_argument("areas_csv", help="CSV with columns: zip,county,state")
    p_score.add_argument("--years", type=int, default=5, help="Lookback window for storm events (default 5)")
    p_score.add_argument("--storm-weight", type=float, default=3.0,
                          help="Points added to priority score per storm event (default 3.0)")
    p_score.add_argument("--api-key", default=None, help="Census API key (optional)")
    p_score.add_argument("--out", default=None, help="Output CSV path (default: print to stdout)")
    p_score.set_defaults(func=cmd_score)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
