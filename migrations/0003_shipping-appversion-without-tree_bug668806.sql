BEGIN;
ALTER TABLE `shipping_appversion` MODIFY COLUMN `tree_id` integer;
COMMIT;
