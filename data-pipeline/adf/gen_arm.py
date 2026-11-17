"""Generates data-pipeline/adf/arm_template.json (one parameterized ADF pipeline)."""
import json, sys

def m(pairs):
    return {"type": "TabularTranslator",
            "mappings": [{"source": {"path": f"$['{s}']", "type": "String"}, "sink": {"name": d, "type": "String"}} for s, d in pairs]}

common = [(":id", "source_row_id"), (":updated_at", "source_updated_at")]
austin = common + [(c, c) for c in ["commodity", "commodity_description", "extended_description", "quantity",
        "unit_of_measure", "unit_price", "itm_tot_am", "master_agreement", "contract_name", "purchase_order",
        "award_date", "vendor_code", "lgl_nm", "city", "st"]]
dallas = common + [(c, c) for c in ["rundate", "fy", "fm", "docid", "chksubtot", "vcode", "vendor", "fundtype",
        "department", "activity", "objectgroup", "object", "commoditydscr", "invoicedate", "invoicenumber"]]
texas = common + [(c, c) for c in ["customer", "vendor", "business_line", "resource_unit_group",
        "resource_unit_sub_group", "resource_unit", "vendor_resource_unit", "start_time", "unit_type",
        "current_month_charges", "dir_recovery_fee", "total_charges", "units", "chargeback_rate"]]

sources = [
    {"name": "austin", "government": "Austin", "baseUrl": "https://data.austintexas.gov", "datasetId": "3ebq-e9iz", "mapping": m(austin)},
    {"name": "dallas", "government": "Dallas", "baseUrl": "https://www.dallasopendata.com", "datasetId": "x5ih-idh7", "mapping": m(dallas)},
    {"name": "texas", "government": "Texas", "baseUrl": "https://data.texas.gov", "datasetId": "8hps-ztn4", "mapping": m(texas)},
]

F = "[parameters('factoryName')]"
def child(kind, name):
    return f"[concat(parameters('factoryName'), '/{name}')]", f"Microsoft.DataFactory/factories/{kind}"

def res(kind, name, props, deps):
    n, t = child(kind, name)
    return {"type": t, "apiVersion": "2018-06-01", "name": n, "properties": props,
            "dependsOn": ["[resourceId('Microsoft.DataFactory/factories', parameters('factoryName'))]"] +
                         [f"[resourceId('Microsoft.DataFactory/factories/{k}', parameters('factoryName'), '{v}')]" for k, v in deps]}

E = lambda v: {"value": v, "type": "Expression"}

ls_rest = {"type": "RestService", "parameters": {"baseUrl": {"type": "String"}},
           "typeProperties": {"url": "@{linkedService().baseUrl}", "authenticationType": "Anonymous",
                              "enableServerCertificateValidation": True}}
ls_sql = {"type": "AzureSqlDatabase",
          "typeProperties": {"connectionString": "[concat('Data Source=tcp:', parameters('sqlServerName'), '.database.windows.net,1433;Initial Catalog=', parameters('sqlDatabaseName'), ';Encrypt=True;Connection Timeout=60')]"}}
ds_rest = {"type": "RestResource",
           "linkedServiceName": {"referenceName": "LS_Socrata", "type": "LinkedServiceReference",
                                 "parameters": {"baseUrl": "@dataset().baseUrl"}},
           "parameters": {"baseUrl": {"type": "String"}, "relativeUrl": {"type": "String"}},
           "typeProperties": {"relativeUrl": E("@dataset().relativeUrl")}}
ds_sql = {"type": "AzureSqlTable",
          "linkedServiceName": {"referenceName": "LS_AzureSql", "type": "LinkedServiceReference"},
          "parameters": {"schemaName": {"type": "String", "defaultValue": "gov"}, "tableName": {"type": "String"}},
          "typeProperties": {"schema": E("@dataset().schemaName"), "table": E("@dataset().tableName")}}


# ---------------- child pipeline: load one source ----------------
P = "pipeline().parameters"
SRC = f"{P}.source"
STATE = "Get load state"
DELTA = "Get source delta"
WM = f"if({P}.fullReload, '1900-01-01T00:00:00', activity('{STATE}').output.firstRow.watermark)"
WHERE = f"concat(':updated_at>''', {WM}, '''')"
EPOCH = f"div(sub(ticks(activity('{DELTA}').output.firstRow.max_updated_at), ticks('1970-01-01T00:00:00Z')), 10000000)"
PAGE = 50000

sql_ref = lambda table: {"referenceName": "DS_SqlTable", "type": "DatasetReference",
                         "parameters": {"schemaName": "gov", "tableName": table}}
pol = lambda t, r=2: {"timeout": t, "retry": r, "retryIntervalInSeconds": 60}

child_acts = [
    {"name": STATE, "type": "Lookup", "policy": pol("0.00:10:00"),
     "typeProperties": {"firstRowOnly": True, "dataset": sql_ref("source_state"),
                        "source": {"type": "AzureSqlSource", "queryTimeout": "00:05:00", "sqlReaderQuery": E(
                            f"@concat('SELECT COALESCE(CONVERT(varchar(23), watermark, 126), ''1900-01-01T00:00:00'') AS watermark "
                            f"FROM gov.source_state WHERE source = ''', {SRC}.name, '''')")}}},
    # one tiny request: how many rows changed since the watermark, and the newest change time
    {"name": DELTA, "type": "Lookup", "policy": pol("0.00:05:00"),
     "dependsOn": [{"activity": STATE, "dependencyConditions": ["Succeeded"]}],
     "typeProperties": {"firstRowOnly": True,
                        "dataset": {"referenceName": "DS_SocrataJson", "type": "DatasetReference",
                                    "parameters": {"baseUrl": f"@{SRC}.baseUrl",
                                                   "relativeUrl": E(f"@concat('resource/', {SRC}.datasetId, '.json?$select=max(:updated_at),count(*)&$where=', {WHERE})")}},
                        "source": {"type": "RestSource", "requestMethod": "GET", "httpRequestTimeout": "00:02:00"}}},
    {"name": "Set doLoad", "type": "SetVariable",
     "dependsOn": [{"activity": DELTA, "dependencyConditions": ["Succeeded"]}],
     "typeProperties": {"variableName": "doLoad", "value": E(f"@greater(int(activity('{DELTA}').output.firstRow.count), 0)")}},
    {"name": "Copy pages", "type": "Until",
     "dependsOn": [{"activity": "Set doLoad", "dependencyConditions": ["Succeeded"]}],
     "typeProperties": {
         "expression": E(f"@or(not(variables('doLoad')), greaterOrEquals(int(variables('offset')), int(activity('{DELTA}').output.firstRow.count)))"),
         "timeout": "0.03:00:00",
         "activities": [{"name": "If loading", "type": "IfCondition",
                         "typeProperties": {"expression": E("@variables('doLoad')"), "ifTrueActivities": [
             {"name": "Copy page to staging", "type": "Copy", "policy": pol("0.00:30:00"),
              "inputs": [{"referenceName": "DS_SocrataJson", "type": "DatasetReference",
                          "parameters": {"baseUrl": f"@{SRC}.baseUrl", "relativeUrl": E(
                              f"@concat('resource/', {SRC}.datasetId, '.json?$select=:*,*&$order=:id&$limit={PAGE}&$offset=', variables('offset'), '&$where=', {WHERE})")}}],
              "outputs": [{"referenceName": "DS_SqlTable", "type": "DatasetReference",
                           "parameters": {"schemaName": "gov", "tableName": E(f"@concat('stg_', {SRC}.name)")}}],
              "typeProperties": {
                  "source": {"type": "RestSource", "requestMethod": "GET", "httpRequestTimeout": "00:05:00"},
                  "sink": {"type": "AzureSqlSink", "writeBatchSize": 10000, "disableMetricsCollection": True,
                           "preCopyScript": E(f"@if(equals(variables('offset'), '0'), concat('TRUNCATE TABLE gov.stg_', {SRC}.name), 'SELECT 1')")},
                  "enableStaging": False, "dataIntegrationUnits": 2,
                  "translator": E(f"@{SRC}.mapping")}},
             {"name": "Next offset", "type": "SetVariable",
              "dependsOn": [{"activity": "Copy page to staging", "dependencyConditions": ["Succeeded"]}],
              "typeProperties": {"variableName": "nextOffset", "value": E(f"@string(add(int(variables('offset')), {PAGE}))")}},
             {"name": "Advance offset", "type": "SetVariable",
              "dependsOn": [{"activity": "Next offset", "dependencyConditions": ["Succeeded"]}],
              "typeProperties": {"variableName": "offset", "value": E("@variables('nextOffset')")}}]}}]}},
    {"name": "If rows loaded", "type": "IfCondition",
     "dependsOn": [{"activity": "Copy pages", "dependencyConditions": ["Succeeded"]}],
     "typeProperties": {"expression": E("@variables('doLoad')"), "ifTrueActivities": [
         {"name": "Merge into history", "type": "SqlServerStoredProcedure", "policy": pol("0.01:00:00", 1),
          "linkedServiceName": {"referenceName": "LS_AzureSql", "type": "LinkedServiceReference"},
          "typeProperties": {"storedProcedureName": E(f"@concat('gov.usp_merge_', {SRC}.name)"),
                             "storedProcedureParameters": {"published_epoch": {"value": E("@" + EPOCH), "type": "Int64"}}}}]}},
]

pl_child = {
    "description": "Load one Socrata source: count rows changed since the watermark, copy them page by page "
                   "($offset loop, 50k rows) into gov.stg_<source>, then MERGE into gov.raw_<source>.",
    "parameters": {"source": {"type": "Object"}, "fullReload": {"type": "Bool", "defaultValue": False}},
    "variables": {"offset": {"type": "String", "defaultValue": "0"}, "nextOffset": {"type": "String", "defaultValue": "0"},
                  "doLoad": {"type": "Boolean", "defaultValue": False}},
    "activities": child_acts, "annotations": ["mis281n", "procurement"]}

pl_parent = {
    "description": "Weekly refresh of Austin, Dallas and Texas procurement data into Azure SQL (gov schema). "
                   "Runs PL_LoadSource for each source in parallel.",
    "parameters": {"sources": {"type": "Array", "defaultValue": sources},
                   "fullReload": {"type": "Bool", "defaultValue": False}},
    "activities": [{"name": "For each government source", "type": "ForEach",
                    "typeProperties": {"isSequential": False, "batchCount": 3,
                                       "items": E("@pipeline().parameters.sources"),
                                       "activities": [{"name": "Load source", "type": "ExecutePipeline",
                                                       "typeProperties": {"pipeline": {"referenceName": "PL_LoadSource", "type": "PipelineReference"},
                                                                          "waitOnCompletion": True,
                                                                          "parameters": {"source": "@item()",
                                                                                         "fullReload": "@pipeline().parameters.fullReload"}}}]}}],
    "annotations": ["mis281n", "procurement"]}

trigger = {"type": "ScheduleTrigger",
           "typeProperties": {"recurrence": {"frequency": "Week", "interval": 1,
                                             "startTime": "2026-11-17T09:00:00", "timeZone": "Central Standard Time",
                                             "schedule": {"weekDays": ["Monday"], "hours": [9], "minutes": [0]}}},
           "pipelines": [{"pipelineReference": {"referenceName": "PL_RefreshGovData", "type": "PipelineReference"},
                          "parameters": {}}]}

template = {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "factoryName": {"type": "string"},
        "location": {"type": "string", "defaultValue": "[resourceGroup().location]"},
        "sqlServerName": {"type": "string", "defaultValue": "haas-govdata-westus"},
        "sqlDatabaseName": {"type": "string", "defaultValue": "govdata"}},
    "resources": [
        {"type": "Microsoft.DataFactory/factories", "apiVersion": "2018-06-01", "name": F,
         "location": "[parameters('location')]", "identity": {"type": "SystemAssigned"}, "properties": {}},
        res("linkedservices", "LS_Socrata", ls_rest, []),
        res("linkedservices", "LS_AzureSql", ls_sql, []),
        res("datasets", "DS_SocrataJson", ds_rest, [("linkedservices", "LS_Socrata")]),
        res("datasets", "DS_SqlTable", ds_sql, [("linkedservices", "LS_AzureSql")]),
        res("pipelines", "PL_LoadSource", pl_child, [("datasets", "DS_SocrataJson"), ("datasets", "DS_SqlTable"),
                                                     ("linkedservices", "LS_AzureSql")]),
        res("pipelines", "PL_RefreshGovData", pl_parent, [("pipelines", "PL_LoadSource")]),
        res("triggers", "TR_WeeklyMon0900Central", trigger, [("pipelines", "PL_RefreshGovData")]),
    ],
    "outputs": {"principalId": {"type": "string",
                                "value": "[reference(resourceId('Microsoft.DataFactory/factories', parameters('factoryName')), '2018-06-01', 'full').identity.principalId]"}}}

json.dump(template, open(sys.argv[1], "w"), indent=2)
print("ok")
