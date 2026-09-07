# EDDM Income Filter

Helper for filtering USPS EDDM (Every Door Direct Mail) routes by household income.

USPS's EDDM map tool (https://eddm.usps.com) has no public API, so route lists
must be exported manually from the site: pick a zip code, select routes on
the map, and download the route CSV. This tool then helps with the income
side of that workflow.

## Commands

**`zip-income`** — look up ZCTA-level median household income (Census ACS
5-year estimates) for a list of zip codes, as a quick check of which zips
are worth pulling EDDM routes for:

```
python eddm_income_filter.py zip-income 39567 39553 39564 39532 39565 39452 39540
```

Add `--api-key YOUR_CENSUS_KEY` to raise rate limits (free key at
https://api.census.gov/data/key_signup.html); not required for a handful of
zips.

**`filter`** — filter an EDDM route CSV (exported from eddm.usps.com) down to
routes at/above an income threshold:

```
python eddm_income_filter.py filter routes.csv --min-income 100000 --out filtered.csv
```

The CSV must contain an income column (any of: `Median Household Income`,
`Average Household Income`, `Household Income`, `Income`).

## Roof-lead scoring (home age + storm damage)

`roof_lead_finder.py` scores target areas for roof-replacement lead
potential, combining:

- **Home age** — Census ACS median year structure built, by zip.
- **Storm damage history** — NOAA Storm Events Database counts of hail,
  thunderstorm wind, tornado, and hurricane/tropical storm events, by
  county, over a lookback window.

NOAA tracks storms by county, not zip, so you need a small mapping CSV
(`zip,county,state`) for your target areas — see `areas_template.csv`.
Fill in the `county` column (e.g. via a zip-to-county lookup) before
running:

```
python roof_lead_finder.py score areas.csv --years 5 --out leads.csv
```

Output is a CSV ranked by `priority_score` (home age in years + storm
event count × `--storm-weight`, default 3 points/event), so the areas at
the top have the oldest homes and/or the most storm activity.

This is a rough targeting signal, not a per-property inspection — county-level
storm counts don't tell you which individual roofs were hit, and median
year built is a zip-wide estimate, not a specific home's age. Use it to
prioritize which zips/routes to target with EDDM, not as a substitute for
an actual roof inspection.

## Note on this environment

This tool's outbound network access is restricted and cannot reach
`api.census.gov` or `www.ncei.noaa.gov`, so both `zip-income` and
`roof_lead_finder.py score` must be run from a machine with normal
internet access, not from this session.
