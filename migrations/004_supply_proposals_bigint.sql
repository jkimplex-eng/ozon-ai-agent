BEGIN;

ALTER TABLE supply_proposals
    ALTER COLUMN sku TYPE BIGINT USING sku::bigint;

ALTER TABLE supply_proposals
    ALTER COLUMN target_warehouse_id TYPE BIGINT USING target_warehouse_id::bigint;

COMMIT;
