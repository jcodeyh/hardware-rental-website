/* =====================================================================
   Merge procedures: staging -> raw history. Called by ADF after each copy.
   Austin / Dallas republish the whole dataset on every refresh, so their
   Socrata :id values are not trustworthy keys. We key on a SHA-256 of the
   record content plus an ordinal for genuinely identical lines.
   Texas updates incrementally and keeps :id stable, so it keys on :id.
   Re-running a load never creates duplicates.
   ===================================================================== */

CREATE OR ALTER PROCEDURE gov.usp_record_state
    @source varchar(20), @published_epoch bigint, @pulled int, @inserted int, @updated int, @watermark datetime2(3)
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE gov.source_state
       SET source_published_at = DATEADD(SECOND, @published_epoch, '1970-01-01'),
           watermark           = COALESCE(@watermark, watermark),
           last_run_at         = SYSUTCDATETIME(),
           last_rows_pulled    = @pulled,
           last_rows_inserted  = @inserted,
           last_rows_updated   = @updated
     WHERE source = @source;
END;
GO

CREATE OR ALTER PROCEDURE gov.usp_merge_austin @published_epoch bigint
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @now datetime2(0) = SYSUTCDATETIME();
    DECLARE @out TABLE (act nvarchar(10));
    DECLARE @pulled int = (SELECT COUNT(*) FROM gov.stg_austin);
    DECLARE @wm datetime2(3) = (SELECT MAX(TRY_CONVERT(datetime2(3), source_updated_at)) FROM gov.stg_austin);

    WITH h AS (
        SELECT s.*,
               HASHBYTES('SHA2_256', CONCAT(commodity,'|',commodity_description,'|',extended_description,'|',
                   quantity,'|',unit_of_measure,'|',unit_price,'|',itm_tot_am,'|',master_agreement,'|',
                   contract_name,'|',purchase_order,'|',award_date,'|',vendor_code,'|',lgl_nm)) AS row_hash
        FROM gov.stg_austin s
    ), src AS (
        SELECT h.*, ROW_NUMBER() OVER (PARTITION BY row_hash ORDER BY source_row_id) AS dup_ordinal FROM h
    )
    MERGE gov.raw_austin AS t
    USING src AS s ON t.row_hash = s.row_hash AND t.dup_ordinal = s.dup_ordinal
    WHEN MATCHED THEN UPDATE SET
        last_seen_at = @now, source_row_id = s.source_row_id,
        source_updated_at = TRY_CONVERT(datetime2(3), s.source_updated_at)
    WHEN NOT MATCHED THEN INSERT
        (row_hash, dup_ordinal, source_row_id, source_updated_at, first_loaded_at, last_seen_at,
         award_date, commodity, commodity_description, extended_description, quantity, unit_of_measure,
         unit_price, itm_tot_am, master_agreement, contract_name, purchase_order, vendor_code, lgl_nm, city, st)
    VALUES
        (s.row_hash, s.dup_ordinal, s.source_row_id, TRY_CONVERT(datetime2(3), s.source_updated_at), @now, @now,
         TRY_CONVERT(datetime2(0), s.award_date), s.commodity, s.commodity_description, s.extended_description,
         TRY_CONVERT(decimal(19,4), s.quantity), s.unit_of_measure, TRY_CONVERT(decimal(19,4), s.unit_price),
         TRY_CONVERT(decimal(19,2), s.itm_tot_am), s.master_agreement, s.contract_name, s.purchase_order,
         s.vendor_code, s.lgl_nm, s.city, s.st)
    OUTPUT $action INTO @out;

    DECLARE @ins int = (SELECT COUNT(*) FROM @out WHERE act = 'INSERT');
    DECLARE @upd int = (SELECT COUNT(*) FROM @out WHERE act = 'UPDATE');
    EXEC gov.usp_record_state 'austin', @published_epoch, @pulled, @ins, @upd, @wm;
    TRUNCATE TABLE gov.stg_austin;
END;
GO

CREATE OR ALTER PROCEDURE gov.usp_merge_dallas @published_epoch bigint
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @now datetime2(0) = SYSUTCDATETIME();
    DECLARE @out TABLE (act nvarchar(10));
    DECLARE @pulled int = (SELECT COUNT(*) FROM gov.stg_dallas);
    DECLARE @wm datetime2(3) = (SELECT MAX(TRY_CONVERT(datetime2(3), source_updated_at)) FROM gov.stg_dallas);

    WITH h AS (
        SELECT s.*,
               HASHBYTES('SHA2_256', CONCAT(rundate,'|',fy,'|',fm,'|',docid,'|',chksubtot,'|',vcode,'|',vendor,'|',
                   fundtype,'|',department,'|',activity,'|',objectgroup,'|',object,'|',commoditydscr,'|',
                   invoicedate,'|',invoicenumber)) AS row_hash
        FROM gov.stg_dallas s
    ), src AS (
        SELECT h.*, ROW_NUMBER() OVER (PARTITION BY row_hash ORDER BY source_row_id) AS dup_ordinal FROM h
    )
    MERGE gov.raw_dallas AS t
    USING src AS s ON t.row_hash = s.row_hash AND t.dup_ordinal = s.dup_ordinal
    WHEN MATCHED THEN UPDATE SET
        last_seen_at = @now, source_row_id = s.source_row_id,
        source_updated_at = TRY_CONVERT(datetime2(3), s.source_updated_at)
    WHEN NOT MATCHED THEN INSERT
        (row_hash, dup_ordinal, source_row_id, source_updated_at, first_loaded_at, last_seen_at,
         rundate, fy, fm, docid, chksubtot, vcode, vendor, fundtype, department, activity,
         objectgroup, object, commoditydscr, invoicedate, invoicenumber)
    VALUES
        (s.row_hash, s.dup_ordinal, s.source_row_id, TRY_CONVERT(datetime2(3), s.source_updated_at), @now, @now,
         TRY_CONVERT(datetime2(0), s.rundate), TRY_CONVERT(int, s.fy), TRY_CONVERT(int, s.fm), s.docid,
         TRY_CONVERT(decimal(19,2), s.chksubtot), s.vcode, s.vendor, s.fundtype, s.department, s.activity,
         s.objectgroup, s.object, s.commoditydscr, s.invoicedate, s.invoicenumber)
    OUTPUT $action INTO @out;

    DECLARE @ins int = (SELECT COUNT(*) FROM @out WHERE act = 'INSERT');
    DECLARE @upd int = (SELECT COUNT(*) FROM @out WHERE act = 'UPDATE');
    EXEC gov.usp_record_state 'dallas', @published_epoch, @pulled, @ins, @upd, @wm;
    TRUNCATE TABLE gov.stg_dallas;
END;
GO

CREATE OR ALTER PROCEDURE gov.usp_merge_texas @published_epoch bigint
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @now datetime2(0) = SYSUTCDATETIME();
    DECLARE @out TABLE (act nvarchar(10));
    DECLARE @pulled int = (SELECT COUNT(*) FROM gov.stg_texas);
    DECLARE @wm datetime2(3) = (SELECT MAX(TRY_CONVERT(datetime2(3), source_updated_at)) FROM gov.stg_texas);

    WITH src AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY source_row_id ORDER BY source_updated_at DESC) AS rn
        FROM gov.stg_texas WHERE source_row_id IS NOT NULL
    )
    MERGE gov.raw_texas AS t
    USING (SELECT * FROM src WHERE rn = 1) AS s ON t.source_row_id = s.source_row_id
    WHEN MATCHED THEN UPDATE SET
        last_seen_at = @now,
        source_updated_at = TRY_CONVERT(datetime2(3), s.source_updated_at),
        start_time = TRY_CONVERT(datetime2(0), s.start_time),
        customer = s.customer, vendor = s.vendor, business_line = s.business_line,
        resource_unit_group = s.resource_unit_group, resource_unit_sub_group = s.resource_unit_sub_group,
        resource_unit = s.resource_unit, vendor_resource_unit = s.vendor_resource_unit, unit_type = s.unit_type,
        current_month_charges = TRY_CONVERT(decimal(19,2), s.current_month_charges),
        dir_recovery_fee = TRY_CONVERT(decimal(19,2), s.dir_recovery_fee),
        total_charges = TRY_CONVERT(decimal(19,2), s.total_charges),
        units = TRY_CONVERT(decimal(19,4), s.units),
        chargeback_rate = TRY_CONVERT(decimal(19,6), s.chargeback_rate)
    WHEN NOT MATCHED THEN INSERT
        (source_row_id, source_updated_at, first_loaded_at, last_seen_at, start_time, customer, vendor,
         business_line, resource_unit_group, resource_unit_sub_group, resource_unit, vendor_resource_unit,
         unit_type, current_month_charges, dir_recovery_fee, total_charges, units, chargeback_rate)
    VALUES
        (s.source_row_id, TRY_CONVERT(datetime2(3), s.source_updated_at), @now, @now,
         TRY_CONVERT(datetime2(0), s.start_time), s.customer, s.vendor, s.business_line, s.resource_unit_group,
         s.resource_unit_sub_group, s.resource_unit, s.vendor_resource_unit, s.unit_type,
         TRY_CONVERT(decimal(19,2), s.current_month_charges), TRY_CONVERT(decimal(19,2), s.dir_recovery_fee),
         TRY_CONVERT(decimal(19,2), s.total_charges), TRY_CONVERT(decimal(19,4), s.units),
         TRY_CONVERT(decimal(19,6), s.chargeback_rate))
    OUTPUT $action INTO @out;

    DECLARE @ins int = (SELECT COUNT(*) FROM @out WHERE act = 'INSERT');
    DECLARE @upd int = (SELECT COUNT(*) FROM @out WHERE act = 'UPDATE');
    EXEC gov.usp_record_state 'texas', @published_epoch, @pulled, @ins, @upd, @wm;
    TRUNCATE TABLE gov.stg_texas;
END;
GO
