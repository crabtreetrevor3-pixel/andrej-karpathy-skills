#!/usr/bin/env python3
"""
Filter USPS EDDM (Every Door Direct Mail) routes by household income.

USPS's EDDM map tool (eddm.usps.com) doesn't expose an API, so route lists
must be exported manually from the site (select a zip -> select routes ->
download route CSV) and passed to this script. This tool then:

  1. filter  - filters an exported EDDM route CSV to routes at/above an
               income threshold (uses whatever income column is present
               in the export).
  2. zip-income - looks up ZCTA-level median household income for a list
               of zip codes via the Census ACS 5-year API, as a quick
               cross-check of which zips are worth pulling routes for.

Usage:
    python eddm_income_filter.py zip-income 39567 39553 39564 39532 39565 39452 39540
    python eddm_income_filter.py filter routes.csv --min-income 100000 --out filtered.csv
"""
import argparse
import csv
import json
import sys
import urllib.request

CENSUS_ACS_URL = "https://api.census.gov/data/2022/acs/acs5"
INCOME_COLUMN_CANDIDATES = [
    "median household income",
    "median_household_income",
    "avg household income",
    "average household income",
    "household income",
    "income",
]


def fetch_zip_income(zip_codes, api_key=None):
    """Return {zip: median_household_income} using ACS 5-year ZCTA estimates."""
    params = f"get=NAME,B19013_001E&for=zip%20code%20tabulation%20area:{','.join(zip_codes)}"
    if api_key:
        params += f"&key={api_key}"
    url = f"{CENSUS_ACS_URL}?{params}"
    with urllib.request.urlopen(url) as resp:
        rows = json.loads(resp.read().decode())
    header, data = rows[0], rows[1:]
    zcta_idx = header.index("zip code tabulation area")
    income_idx = header.index("B19013_001E")
    return {row[zcta_idx]: int(row[income_idx]) for row in data if row[income_idx] not in (None, "null")}


def cmd_zip_income(args):
    incomes = fetch_zip_income(args.zip_codes, api_key=args.api_key)
    print(f"{'ZIP':<8}{'Median HH Income':>18}{'>= threshold':>15}")
    for z in args.zip_codes:
        income = incomes.get(z)
        if income is None:
            print(f"{z:<8}{'no data':>18}{'':>15}")
            continue
        flag = "yes" if income >= args.min_income else "no"
        print(f"{z:<8}{income:>18,}{flag:>15}")


def find_income_column(fieldnames):
    lowered = {f.lower().strip(): f for f in fieldnames}
    for candidate in INCOME_COLUMN_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    return None


def cmd_filter(args):
    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        income_col = find_income_column(reader.fieldnames or [])
        if not income_col:
            sys.exit(
                "No income column found in CSV. Expected one of: "
                + ", ".join(INCOME_COLUMN_CANDIDATES)
            )
        rows = list(reader)

    def income_value(row):
        raw = row[income_col].replace("$", "").replace(",", "").strip()
        return float(raw) if raw else None

    filtered = [r for r in rows if (v := income_value(r)) is not None and v >= args.min_income]

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(filtered)
        print(f"Wrote {len(filtered)} of {len(rows)} routes (income >= {args.min_income:,}) to {args.out}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(filtered)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_zip = sub.add_parser("zip-income", help="Look up ZCTA-level median household income for zip codes")
    p_zip.add_argument("zip_codes", nargs="+", help="Zip codes to look up")
    p_zip.add_argument("--min-income", type=int, default=100000)
    p_zip.add_argument("--api-key", default=None, help="Census API key (optional, raises rate limits)")
    p_zip.set_defaults(func=cmd_zip_income)

    p_filter = sub.add_parser("filter", help="Filter an exported EDDM route CSV by income")
    p_filter.add_argument("csv_path", help="Path to EDDM route CSV exported from eddm.usps.com")
    p_filter.add_argument("--min-income", type=int, default=100000)
    p_filter.add_argument("--out", default=None, help="Output CSV path (default: print to stdout)")
    p_filter.set_defaults(func=cmd_filter)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
