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

## Note on this environment

This tool's outbound network access is restricted and cannot reach
`api.census.gov`, so `zip-income` must be run from a machine with normal
internet access, not from this session.
