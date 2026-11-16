#!/usr/bin/env bash
# Deploy the government-data pipeline from Azure Cloud Shell (bash).
#   ./deploy.sh check    read-only: shows SQL tier/free offer, firewall, ADF regions
#   ./deploy.sh sql      runs sql/*.sql in hardwarerental (temporary firewall rule for this shell)
#   ./deploy.sh adf      deploys Data Factory + pipeline + trigger (trigger stays stopped)
#   ./deploy.sh grant    lets the factory's managed identity read/write the gov schema
#   ./deploy.sh run      starts a pipeline run (FULL=true for a full reload)
#   ./deploy.sh start    turns on the weekly Monday 09:00 Central trigger
set -euo pipefail
cd "$(dirname "$0")"
export PATH=~/bin:$PATH
az config set extension.use_dynamic_install=yes_without_prompt -o none 2>/dev/null || true

SQL_SERVER=${SQL_SERVER:-haas-govdata-westus}
SQL_DB=${SQL_DB:-govdata}
ADF_NAME=${ADF_NAME:-adf-haas-govdata}
RG=${RG:-$(az sql server list --query "[?name=='$SQL_SERVER'].resourceGroup | [0]" -o tsv)}
ADF_LOCATION=${ADF_LOCATION:-westus}

sqlrun() {  # sqlrun <file|-q query>
  if ! command -v sqlcmd >/dev/null; then   # Cloud Shell ships without sqlcmd
    mkdir -p ~/bin && curl -sL https://github.com/microsoft/go-sqlcmd/releases/latest/download/sqlcmd-linux-amd64.tar.bz2 | tar xj -C ~/bin
    fi
  local ip; ip=$(curl -s https://api.ipify.org)
  az sql server firewall-rule create -g "$RG" -s "$SQL_SERVER" -n cloudshell-temp --start-ip-address "$ip" --end-ip-address "$ip" -o none
  local rc=0
  until sqlcmd -S "$SQL_SERVER.database.windows.net" -d "$SQL_DB" --authentication-method ActiveDirectoryAzCli -Q "SELECT 1" -b >/dev/null 2>&1; do
    echo "waiting for $SQL_DB to resume..."; sleep 15; done
  sqlcmd -S "$SQL_SERVER.database.windows.net" -d "$SQL_DB" --authentication-method ActiveDirectoryAzCli -b "$@" || rc=$?
  az sql server firewall-rule delete -g "$RG" -s "$SQL_SERVER" -n cloudshell-temp -o none
  return $rc
}

case "${1:-check}" in
  check)
    echo "Resource group: $RG"
    az sql db show -g "$RG" -s "$SQL_SERVER" -n "$SQL_DB" \
      --query "{sku:currentSku.name, tier:currentSku.tier, freeOffer:useFreeLimit, whenFreeUsedUp:freeLimitExhaustionBehavior, autoPauseMin:autoPauseDelay, maxGB:maxSizeBytes}" -o table
    echo "Entra admin:"; az sql server ad-admin list -g "$RG" -s "$SQL_SERVER" --query "[].login" -o tsv
    echo "Firewall rules:"; az sql server firewall-rule list -g "$RG" -s "$SQL_SERVER" --query "[].{name:name,start:startIpAddress,end:endIpAddress}" -o table
    echo "Existing factories:"; az resource list -g "$RG" --resource-type Microsoft.DataFactory/factories --query "[].{name:name,location:location}" -o table
    echo "Data Factory regions:"; az provider show -n Microsoft.DataFactory --query "resourceTypes[?resourceType=='factories'].locations | [0]" -o tsv | tr '\n' ',' ; echo
    ;;
  sql)
    for f in sql/01_schema.sql sql/02_merge_procs.sql; do echo "== $f"; sqlrun -i "$f"; done
    ;;
  adf)
    az deployment group create -g "$RG" -n govdata-adf --template-file adf/arm_template.json \
      --parameters factoryName="$ADF_NAME" sqlServerName="$SQL_SERVER" sqlDatabaseName="$SQL_DB" \
      ${ADF_LOCATION:+location=$ADF_LOCATION} --query properties.outputs -o json
    ;;
  grant)
    sqlrun -Q "IF USER_ID('$ADF_NAME') IS NULL CREATE USER [$ADF_NAME] FROM EXTERNAL PROVIDER;
               GRANT SELECT, INSERT, UPDATE, DELETE, ALTER, EXECUTE ON SCHEMA::gov TO [$ADF_NAME];"
    ;;
  run)
    az datafactory pipeline create-run -g "$RG" --factory-name "$ADF_NAME" -n PL_RefreshGovData \
      --parameters "{\"fullReload\": ${FULL:-false}}" --query runId -o tsv
    ;;
  status)
    az datafactory pipeline-run query-by-factory -g "$RG" --factory-name "$ADF_NAME" \
      --last-updated-after "$(date -u -d '-1 day' +%FT%TZ)" --last-updated-before "$(date -u -d '+1 hour' +%FT%TZ)" \
      --query "value[].{run:runId,status:status,start:runStart,ms:durationInMs,msg:message}" -o table
    ;;
  test)
    sqlrun -i sql/03_test_queries.sql -W -s " | "
    ;;
  reset)   # wipe loaded data + watermarks (use before a clean full reload)
    sqlrun -Q "TRUNCATE TABLE gov.raw_austin; TRUNCATE TABLE gov.raw_dallas; TRUNCATE TABLE gov.raw_texas;
               TRUNCATE TABLE gov.stg_austin; TRUNCATE TABLE gov.stg_dallas; TRUNCATE TABLE gov.stg_texas;
               UPDATE gov.source_state SET source_published_at=NULL, watermark=NULL, last_run_at=NULL,
                      last_rows_pulled=NULL, last_rows_inserted=NULL, last_rows_updated=NULL;
               SELECT source, watermark FROM gov.source_state;"
    ;;
  cancel)
    for r in $(az datafactory pipeline-run query-by-factory -g "$RG" --factory-name "$ADF_NAME" \
        --last-updated-after "$(date -u -d '-1 day' +%FT%TZ)" --last-updated-before "$(date -u -d '+1 hour' +%FT%TZ)" \
        --query "value[?status=='InProgress' || status=='Queued'].runId" -o tsv); do
      az datafactory pipeline-run cancel -g "$RG" --factory-name "$ADF_NAME" --run-id "$r" --is-recursive true && echo "cancelled $r"
    done
    ;;
  steps)   # per-activity detail for the newest run (child pipelines included)
    since="$(date -u -d '-1 day' +%FT%TZ)"; until_="$(date -u -d '+1 hour' +%FT%TZ)"
    for r in $(az datafactory pipeline-run query-by-factory -g "$RG" --factory-name "$ADF_NAME" --last-updated-after "$since" --last-updated-before "$until_" \
        --query "sort_by(value,&runStart)[-4:].runId" -o tsv); do
      az datafactory activity-run query-by-pipeline-run -g "$RG" --factory-name "$ADF_NAME" --run-id "$r" --last-updated-after "$since" --last-updated-before "$until_" \
        --query "value[?activityType!='SetVariable'].{pipeline:pipelineName, activity:activityName, status:status, rows:output.rowsCopied, err:error.message}" -o table
    done
    ;;
  start)
    az datafactory trigger start -g "$RG" --factory-name "$ADF_NAME" -n TR_WeeklyMon0900Central
    ;;
  *) echo "unknown step"; exit 1 ;;
esac
