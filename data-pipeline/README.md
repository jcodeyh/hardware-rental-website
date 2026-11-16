# Government procurement data pipeline (Azure Data Factory → Azure SQL)

Pulls Austin, Dallas and Texas procurement data from their live Socrata APIs into the
`hardwarerental` Azure SQL database (schema `gov`) and refreshes it daily.

| Path | What |
|---|---|
| `sql/01_schema.sql` | staging, raw history tables, `gov.purchases` view, `gov.source_state` |
| `sql/02_merge_procs.sql` | idempotent staging → history merges (content hash for Austin/Dallas, `:id` for Texas) |
| `sql/03_test_queries.sql` | grading / demo queries (date ranges, freshness, duplicate check) |
| `adf/arm_template.json` | Data Factory, linked services, datasets, `PL_RefreshGovData`, daily trigger |
| `adf/gen_arm.py` | generates the template (edit sources/mappings here) |
| `deploy.sh` | Cloud Shell steps: `check`, `sql`, `adf`, `grant`, `run`, `status`, `steps`, `test`, `reset`, `cancel`, `start` |

## Pipelines
`PL_RefreshGovData` (daily trigger) runs `PL_LoadSource` once per source, 3 in parallel. `PL_LoadSource`:
1. **Lookup** `gov.source_state` → last `:updated_at` watermark.
2. **Lookup** (REST) `$select=max(:updated_at),count(*)&$where=:updated_at>'<watermark>'` → rows changed.
3. **Until** offset ≥ count: **Copy** one page (`$order=:id&$limit=50000&$offset=<n>`) → `gov.stg_<source>`
   (first page truncates staging). ADF's built-in REST paging can't read a bare JSON array, hence the loop.
4. **If** rows were copied: stored procedure `gov.usp_merge_<source>` merges into `gov.raw_<source>` and records counts + watermark.

No changed rows → two lookups, no copy.

## Deploy (Azure Cloud Shell, bash)
```bash
git clone -b data-factory-pipeline https://github.com/jcodeyh/hardware-rental-website.git
cd hardware-rental-website/data-pipeline
./deploy.sh check          # read-only
./deploy.sh sql            # create schema + procs
./deploy.sh adf            # create factory + pipeline (trigger stopped)
./deploy.sh grant          # managed identity → gov schema
FULL=true ./deploy.sh run  # first full load
./deploy.sh status
./deploy.sh test
./deploy.sh start          # daily 06:00 Central
```
