/* =====================================================================
   Government procurement data - schema (Azure SQL: hardwarerental)
   Layers:
     gov.stg_<source>   landing table, truncated by ADF before each copy
     gov.raw_<source>   typed history, one row per source record, never purged
     gov.purchases      view: one shared shape across Austin, Dallas, Texas
     gov.source_state   change-detection watermark per source
   Re-runnable: drops and recreates staging + view, keeps raw history.
   ===================================================================== */
IF SCHEMA_ID('gov') IS NULL EXEC('CREATE SCHEMA gov');
GO

/* ---------- staging (all text; ADF writes exactly what the API returns) ---------- */
DROP TABLE IF EXISTS gov.stg_austin;
CREATE TABLE gov.stg_austin (
    source_row_id        nvarchar(64),
    source_updated_at    nvarchar(40),
    commodity            nvarchar(50),
    commodity_description nvarchar(400),
    extended_description nvarchar(max),
    quantity             nvarchar(40),
    unit_of_measure      nvarchar(20),
    unit_price           nvarchar(40),
    itm_tot_am           nvarchar(40),
    master_agreement     nvarchar(60),
    contract_name        nvarchar(400),
    purchase_order       nvarchar(60),
    award_date           nvarchar(40),
    vendor_code          nvarchar(40),
    lgl_nm               nvarchar(400),
    city                 nvarchar(100),
    st                   nvarchar(10)
);

DROP TABLE IF EXISTS gov.stg_dallas;
CREATE TABLE gov.stg_dallas (
    source_row_id     nvarchar(64),
    source_updated_at nvarchar(40),
    rundate           nvarchar(40),
    fy                nvarchar(10),
    fm                nvarchar(10),
    docid             nvarchar(60),
    chksubtot         nvarchar(40),
    vcode             nvarchar(40),
    vendor            nvarchar(400),
    fundtype          nvarchar(200),
    department        nvarchar(200),
    activity          nvarchar(200),
    objectgroup       nvarchar(200),
    object            nvarchar(200),
    commoditydscr     nvarchar(400),
    invoicedate       nvarchar(40),
    invoicenumber     nvarchar(100)
);

DROP TABLE IF EXISTS gov.stg_texas;
CREATE TABLE gov.stg_texas (
    source_row_id           nvarchar(64),
    source_updated_at       nvarchar(40),
    customer                nvarchar(200),
    vendor                  nvarchar(200),
    business_line           nvarchar(200),
    resource_unit_group     nvarchar(200),
    resource_unit_sub_group nvarchar(200),
    resource_unit           nvarchar(400),
    vendor_resource_unit    nvarchar(400),
    start_time              nvarchar(40),
    unit_type               nvarchar(60),
    current_month_charges   nvarchar(40),
    dir_recovery_fee        nvarchar(40),
    total_charges           nvarchar(40),
    units                   nvarchar(40),
    chargeback_rate         nvarchar(40)
);
GO

/* ---------- raw history (typed) ---------- */
IF OBJECT_ID('gov.raw_austin') IS NULL
CREATE TABLE gov.raw_austin (
    row_id               bigint IDENTITY PRIMARY KEY,
    row_hash             binary(32)   NOT NULL,   -- SHA-256 of record content
    dup_ordinal          int          NOT NULL,   -- keeps genuinely identical lines
    source_row_id        nvarchar(64) NULL,       -- Socrata :id (changes on republish)
    source_updated_at    datetime2(3) NULL,
    first_loaded_at      datetime2(0) NOT NULL,
    last_seen_at         datetime2(0) NOT NULL,
    award_date           datetime2(0) NULL,
    commodity            nvarchar(50) NULL,
    commodity_description nvarchar(400) NULL,
    extended_description nvarchar(max) NULL,
    quantity             decimal(19,4) NULL,
    unit_of_measure      nvarchar(20) NULL,
    unit_price           decimal(19,4) NULL,
    itm_tot_am           decimal(19,2) NULL,
    master_agreement     nvarchar(60) NULL,
    contract_name        nvarchar(400) NULL,
    purchase_order       nvarchar(60) NULL,
    vendor_code          nvarchar(40) NULL,
    lgl_nm               nvarchar(400) NULL,
    city                 nvarchar(100) NULL,
    st                   nvarchar(10) NULL,
    CONSTRAINT uq_raw_austin UNIQUE (row_hash, dup_ordinal)
);

IF OBJECT_ID('gov.raw_dallas') IS NULL
CREATE TABLE gov.raw_dallas (
    row_id            bigint IDENTITY PRIMARY KEY,
    row_hash          binary(32)   NOT NULL,
    dup_ordinal       int          NOT NULL,
    source_row_id     nvarchar(64) NULL,
    source_updated_at datetime2(3) NULL,
    first_loaded_at   datetime2(0) NOT NULL,
    last_seen_at      datetime2(0) NOT NULL,
    rundate           datetime2(0) NULL,
    fy                int NULL,
    fm                int NULL,
    docid             nvarchar(60) NULL,
    chksubtot         decimal(19,2) NULL,
    vcode             nvarchar(40) NULL,
    vendor            nvarchar(400) NULL,
    fundtype          nvarchar(200) NULL,
    department        nvarchar(200) NULL,
    activity          nvarchar(200) NULL,
    objectgroup       nvarchar(200) NULL,
    object            nvarchar(200) NULL,
    commoditydscr     nvarchar(400) NULL,
    invoicedate       nvarchar(40) NULL,
    invoicenumber     nvarchar(100) NULL,
    CONSTRAINT uq_raw_dallas UNIQUE (row_hash, dup_ordinal)
);

IF OBJECT_ID('gov.raw_texas') IS NULL
CREATE TABLE gov.raw_texas (
    row_id                  bigint IDENTITY PRIMARY KEY,
    source_row_id           nvarchar(64) NOT NULL,  -- Texas :id is stable (true incremental updates)
    source_updated_at       datetime2(3) NULL,
    first_loaded_at         datetime2(0) NOT NULL,
    last_seen_at            datetime2(0) NOT NULL,
    start_time              datetime2(0) NULL,
    customer                nvarchar(200) NULL,
    vendor                  nvarchar(200) NULL,
    business_line           nvarchar(200) NULL,
    resource_unit_group     nvarchar(200) NULL,
    resource_unit_sub_group nvarchar(200) NULL,
    resource_unit           nvarchar(400) NULL,
    vendor_resource_unit    nvarchar(400) NULL,
    unit_type               nvarchar(60) NULL,
    current_month_charges   decimal(19,2) NULL,
    dir_recovery_fee        decimal(19,2) NULL,
    total_charges           decimal(19,2) NULL,
    units                   decimal(19,4) NULL,
    chargeback_rate         decimal(19,6) NULL,
    CONSTRAINT uq_raw_texas UNIQUE (source_row_id)
);
GO

/* indexes for date-range and per-government queries */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_raw_austin_date')
    CREATE INDEX ix_raw_austin_date ON gov.raw_austin (award_date) INCLUDE (lgl_nm, commodity_description, itm_tot_am, unit_price, quantity);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_raw_dallas_date')
    CREATE INDEX ix_raw_dallas_date ON gov.raw_dallas (rundate) INCLUDE (vendor, commoditydscr, object, chksubtot);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_raw_texas_date')
    CREATE INDEX ix_raw_texas_date ON gov.raw_texas (start_time) INCLUDE (vendor, business_line, total_charges);
GO

/* ---------- change-detection state ---------- */
IF OBJECT_ID('gov.source_state') IS NULL
CREATE TABLE gov.source_state (
    source              varchar(20)  NOT NULL PRIMARY KEY,
    government          varchar(20)  NOT NULL,
    source_published_at datetime2(0) NULL,   -- dataset rowsUpdatedAt at last successful load
    watermark           datetime2(3) NULL,   -- max :updated_at loaded
    last_run_at         datetime2(0) NULL,
    last_rows_pulled    int NULL,
    last_rows_inserted  int NULL,
    last_rows_updated   int NULL
);
MERGE gov.source_state AS t
USING (VALUES ('austin','Austin'),('dallas','Dallas'),('texas','Texas')) AS s(source, government)
ON t.source = s.source
WHEN NOT MATCHED THEN INSERT (source, government) VALUES (s.source, s.government);
GO

/* ---------- shared shape (field names agreed with the team) ---------- */
CREATE OR ALTER VIEW gov.purchases AS
SELECT  'Austin'                        AS government,
        a.award_date                    AS record_date,
        a.lgl_nm                        AS vendor,
        a.commodity_description         AS category,
        a.extended_description          AS item,
        CAST('City of Austin' AS nvarchar(200)) AS buyer,
        a.quantity                      AS quantity,
        a.unit_price                    AS unit_price,
        CAST(a.itm_tot_am AS decimal(19,2)) AS amount,
        a.source_updated_at             AS updated_at,
        a.last_seen_at                  AS last_seen_at,
        CONCAT('austin-', a.row_id)     AS record_key
FROM gov.raw_austin a
UNION ALL
SELECT  'Dallas',
        d.rundate,
        d.vendor,
        CASE WHEN d.commoditydscr IS NULL OR d.commoditydscr = 'NONE' THEN d.object ELSE d.commoditydscr END,
        d.object,
        d.department,
        NULL,
        NULL,
        d.chksubtot,
        d.source_updated_at,
        d.last_seen_at,
        CONCAT('dallas-', d.row_id)
FROM gov.raw_dallas d
UNION ALL
SELECT  'Texas',
        t.start_time,
        t.vendor,
        t.business_line,
        t.resource_unit,
        t.customer,
        t.units,
        t.chargeback_rate,
        t.total_charges,
        t.source_updated_at,
        t.last_seen_at,
        CONCAT('texas-', t.row_id)
FROM gov.raw_texas t;
GO
