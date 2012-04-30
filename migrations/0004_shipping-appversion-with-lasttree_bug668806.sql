/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

ALTER TABLE `shipping_appversion` ADD COLUMN `lasttree_id` integer;
ALTER TABLE `shipping_appversion` ADD CONSTRAINT `lasttree_id_refs_id_49af3e12` FOREIGN KEY (`lasttree_id`) REFERENCES `life_tree` (`id`);
