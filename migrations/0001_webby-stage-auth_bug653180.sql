/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

ALTER TABLE `webby_project` ADD `stage_login` varchar(80);
ALTER TABLE `webby_project` ADD `stage_passwd` varchar(80);
ALTER TABLE `webby_project` ADD `stage_auth_url` varchar(250);
