/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


/*
 * For this to work, you need to set up your mysql server's time_zone
 * system table otherwise it won't know what the daylight savings
 * implications are for things like America/Los_Angeles
 * You need to run:
 *
 *   mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u myusername -p mysql
 *
 * This should work out-of-the-box linux and mysql installed with homebrew
 * on OSX.
 * Note: You need to supply your own authentication but it's important that
 * you pipe this into the sytem table `mysql`.
 * To test that it worked try:
 *

 mysql> select CONVERT_TZ('2010-06-01 11:48:37', 'America/Los_Angeles', 'UTC');
 +-----------------------------------------------------------------+
 | CONVERT_TZ('2010-06-01 11:48:37', 'America/Los_Angeles', 'UTC') |
 +-----------------------------------------------------------------+
 | 2010-06-01 18:48:37                                             |
 +-----------------------------------------------------------------+
 1 row in set (0.00 sec)

 *
 * If you get NULL instead of a date it means your `mysql` database
 * probably has an empty `time_zone` table.
 *
 */


UPDATE shipping_signoff
       SET `when` = CONVERT_TZ(`when`, 'America/Los_Angeles', 'UTC');

UPDATE shipping_action
       SET `when` = CONVERT_TZ(`when`, 'America/Los_Angeles', 'UTC');
