ALTER TABLE `shipping_appversion` ADD COLUMN `lasttree_id` integer;
ALTER TABLE `shipping_appversion` ADD CONSTRAINT `lasttree_id_refs_id_49af3e12` FOREIGN KEY (`lasttree_id`) REFERENCES `life_tree` (`id`);
