/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

### New Model: djcelery.TaskMeta
CREATE TABLE `celery_taskmeta` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `task_id` varchar(255) NOT NULL UNIQUE,
    `status` varchar(50) NOT NULL,
    `result` longtext,
    `date_done` datetime NOT NULL,
    `traceback` longtext
)
;
### New Model: djcelery.TaskSetMeta
CREATE TABLE `celery_tasksetmeta` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `taskset_id` varchar(255) NOT NULL UNIQUE,
    `result` longtext NOT NULL,
    `date_done` datetime NOT NULL
)
;
### New Model: djcelery.IntervalSchedule
CREATE TABLE `djcelery_intervalschedule` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `every` integer NOT NULL,
    `period` varchar(24) NOT NULL
)
;
### New Model: djcelery.CrontabSchedule
CREATE TABLE `djcelery_crontabschedule` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `minute` varchar(64) NOT NULL,
    `hour` varchar(64) NOT NULL,
    `day_of_week` varchar(64) NOT NULL
)
;
### New Model: djcelery.PeriodicTasks
CREATE TABLE `djcelery_periodictasks` (
    `ident` smallint NOT NULL PRIMARY KEY,
    `last_update` datetime NOT NULL
)
;
### New Model: djcelery.PeriodicTask
CREATE TABLE `djcelery_periodictask` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(200) NOT NULL UNIQUE,
    `task` varchar(200) NOT NULL,
    `interval_id` integer,
    `crontab_id` integer,
    `args` longtext NOT NULL,
    `kwargs` longtext NOT NULL,
    `queue` varchar(200),
    `exchange` varchar(200),
    `routing_key` varchar(200),
    `expires` datetime,
    `enabled` bool NOT NULL,
    `last_run_at` datetime,
    `total_run_count` integer UNSIGNED NOT NULL,
    `date_changed` datetime NOT NULL
)
;
ALTER TABLE `djcelery_periodictask` ADD CONSTRAINT `interval_id_refs_id_f2054349` FOREIGN KEY (`interval_id`) REFERENCES `djcelery_intervalschedule` (`id`);
ALTER TABLE `djcelery_periodictask` ADD CONSTRAINT `crontab_id_refs_id_ebff5e74` FOREIGN KEY (`crontab_id`) REFERENCES `djcelery_crontabschedule` (`id`);
### New Model: djcelery.WorkerState
CREATE TABLE `djcelery_workerstate` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(255) NOT NULL UNIQUE,
    `last_heartbeat` datetime
)
;
### New Model: djcelery.TaskState
CREATE TABLE `djcelery_taskstate` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `state` varchar(64) NOT NULL,
    `task_id` varchar(36) NOT NULL UNIQUE,
    `name` varchar(200),
    `tstamp` datetime NOT NULL,
    `args` longtext,
    `kwargs` longtext,
    `eta` datetime,
    `expires` datetime,
    `result` longtext,
    `traceback` longtext,
    `runtime` double precision,
    `worker_id` integer,
    `hidden` bool NOT NULL
)
;
ALTER TABLE `djcelery_taskstate` ADD CONSTRAINT `worker_id_refs_id_4e3453a` FOREIGN KEY (`worker_id`) REFERENCES `djcelery_workerstate` (`id`);
### New Model: auth.Permission
CREATE TABLE `auth_permission` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `content_type_id` integer NOT NULL,
    `codename` varchar(100) NOT NULL,
    UNIQUE (`content_type_id`, `codename`)
)
;
### New Model: auth.Group_permissions
CREATE TABLE `auth_group_permissions` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `group_id` integer NOT NULL,
    `permission_id` integer NOT NULL,
    UNIQUE (`group_id`, `permission_id`)
)
;
ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `permission_id_refs_id_a7792de1` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);
### New Model: auth.Group
CREATE TABLE `auth_group` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(80) NOT NULL UNIQUE
)
;
ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `group_id_refs_id_3cea63fe` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
### New Model: auth.User_user_permissions
CREATE TABLE `auth_user_user_permissions` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL,
    `permission_id` integer NOT NULL,
    UNIQUE (`user_id`, `permission_id`)
)
;
ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `permission_id_refs_id_67e79cb` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);
### New Model: auth.User_groups
CREATE TABLE `auth_user_groups` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL,
    `group_id` integer NOT NULL,
    UNIQUE (`user_id`, `group_id`)
)
;
ALTER TABLE `auth_user_groups` ADD CONSTRAINT `group_id_refs_id_f0ee9890` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
### New Model: auth.User
CREATE TABLE `auth_user` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `username` varchar(30) NOT NULL UNIQUE,
    `first_name` varchar(30) NOT NULL,
    `last_name` varchar(30) NOT NULL,
    `email` varchar(75) NOT NULL,
    `password` varchar(128) NOT NULL,
    `is_staff` bool NOT NULL,
    `is_active` bool NOT NULL,
    `is_superuser` bool NOT NULL,
    `last_login` datetime NOT NULL,
    `date_joined` datetime NOT NULL
)
;
ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `user_id_refs_id_f2045483` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `auth_user_groups` ADD CONSTRAINT `user_id_refs_id_831107f1` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
### New Model: auth.Message
CREATE TABLE `auth_message` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL,
    `message` longtext NOT NULL
)
;
ALTER TABLE `auth_message` ADD CONSTRAINT `user_id_refs_id_9af0b65a` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
### New Model: contenttypes.ContentType
CREATE TABLE `django_content_type` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL,
    `app_label` varchar(100) NOT NULL,
    `model` varchar(100) NOT NULL,
    UNIQUE (`app_label`, `model`)
)
;
ALTER TABLE `auth_permission` ADD CONSTRAINT `content_type_id_refs_id_728de91f` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);
### New Model: sessions.Session
CREATE TABLE `django_session` (
    `session_key` varchar(40) NOT NULL PRIMARY KEY,
    `session_data` longtext NOT NULL,
    `expire_date` datetime NOT NULL
)
;
### New Model: admin.LogEntry
CREATE TABLE `django_admin_log` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `action_time` datetime NOT NULL,
    `user_id` integer NOT NULL,
    `content_type_id` integer,
    `object_id` longtext,
    `object_repr` varchar(200) NOT NULL,
    `action_flag` smallint UNSIGNED NOT NULL,
    `change_message` longtext NOT NULL
)
;
ALTER TABLE `django_admin_log` ADD CONSTRAINT `user_id_refs_id_c8665aa` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `django_admin_log` ADD CONSTRAINT `content_type_id_refs_id_288599e6` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);
### New Model: privacy.Policy
CREATE TABLE `privacy_policy` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `text` longtext NOT NULL,
    `active` bool NOT NULL
)
;
### New Model: privacy.Comment
CREATE TABLE `privacy_comment` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `text` longtext NOT NULL,
    `policy_id` integer NOT NULL,
    `who_id` integer NOT NULL
)
;
ALTER TABLE `privacy_comment` ADD CONSTRAINT `policy_id_refs_id_1d963959` FOREIGN KEY (`policy_id`) REFERENCES `privacy_policy` (`id`);
ALTER TABLE `privacy_comment` ADD CONSTRAINT `who_id_refs_id_857807b7` FOREIGN KEY (`who_id`) REFERENCES `auth_user` (`id`);
### New Model: life.Locale
CREATE TABLE `life_locale` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `code` varchar(30) NOT NULL UNIQUE,
    `name` varchar(100),
    `native` varchar(100)
)
;
### New Model: life.Branch
CREATE TABLE `life_branch` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` longtext NOT NULL
)
;
### New Model: life.Changeset_files
CREATE TABLE `life_changeset_files` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `changeset_id` integer NOT NULL,
    `file_id` integer NOT NULL,
    UNIQUE (`changeset_id`, `file_id`)
)
;
### New Model: life.Changeset_parents
CREATE TABLE `life_changeset_parents` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `from_changeset_id` integer NOT NULL,
    `to_changeset_id` integer NOT NULL,
    UNIQUE (`from_changeset_id`, `to_changeset_id`)
)
;
### New Model: life.Changeset
CREATE TABLE `life_changeset` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `revision` varchar(40) NOT NULL UNIQUE,
    `user` varchar(200) NOT NULL,
    `description` longtext,
    `branch_id` integer NOT NULL
)
;
ALTER TABLE `life_changeset` ADD CONSTRAINT `branch_id_refs_id_2146ec18` FOREIGN KEY (`branch_id`) REFERENCES `life_branch` (`id`);
ALTER TABLE `life_changeset_files` ADD CONSTRAINT `changeset_id_refs_id_fd78eb77` FOREIGN KEY (`changeset_id`) REFERENCES `life_changeset` (`id`);
ALTER TABLE `life_changeset_parents` ADD CONSTRAINT `from_changeset_id_refs_id_b3f2d193` FOREIGN KEY (`from_changeset_id`) REFERENCES `life_changeset` (`id`);
ALTER TABLE `life_changeset_parents` ADD CONSTRAINT `to_changeset_id_refs_id_b3f2d193` FOREIGN KEY (`to_changeset_id`) REFERENCES `life_changeset` (`id`);
### New Model: life.Forest
CREATE TABLE `life_forest` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE,
    `url` varchar(200) NOT NULL
)
;
### New Model: life.Repository_changesets
CREATE TABLE `life_repository_changesets` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `repository_id` integer NOT NULL,
    `changeset_id` integer NOT NULL,
    UNIQUE (`repository_id`, `changeset_id`)
)
;
ALTER TABLE `life_repository_changesets` ADD CONSTRAINT `changeset_id_refs_id_9b89973` FOREIGN KEY (`changeset_id`) REFERENCES `life_changeset` (`id`);
### New Model: life.Repository
CREATE TABLE `life_repository` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE,
    `url` varchar(200) NOT NULL,
    `forest_id` integer,
    `locale_id` integer
)
;
ALTER TABLE `life_repository` ADD CONSTRAINT `forest_id_refs_id_2d072a56` FOREIGN KEY (`forest_id`) REFERENCES `life_forest` (`id`);
ALTER TABLE `life_repository` ADD CONSTRAINT `locale_id_refs_id_4af7545b` FOREIGN KEY (`locale_id`) REFERENCES `life_locale` (`id`);
ALTER TABLE `life_repository_changesets` ADD CONSTRAINT `repository_id_refs_id_1b338c40` FOREIGN KEY (`repository_id`) REFERENCES `life_repository` (`id`);
### New Model: life.Push_changesets
CREATE TABLE `life_push_changesets` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `push_id` integer NOT NULL,
    `changeset_id` integer NOT NULL,
    UNIQUE (`push_id`, `changeset_id`)
)
;
ALTER TABLE `life_push_changesets` ADD CONSTRAINT `changeset_id_refs_id_cd40bc89` FOREIGN KEY (`changeset_id`) REFERENCES `life_changeset` (`id`);
### New Model: life.Push
CREATE TABLE `life_push` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `repository_id` integer NOT NULL,
    `user` varchar(200) NOT NULL,
    `push_date` datetime NOT NULL,
    `push_id` integer UNSIGNED NOT NULL
)
;
ALTER TABLE `life_push` ADD CONSTRAINT `repository_id_refs_id_dfa6e2a7` FOREIGN KEY (`repository_id`) REFERENCES `life_repository` (`id`);
ALTER TABLE `life_push_changesets` ADD CONSTRAINT `push_id_refs_id_f19e4dc8` FOREIGN KEY (`push_id`) REFERENCES `life_push` (`id`);
### New Model: life.Tree_repositories
CREATE TABLE `life_tree_repositories` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `tree_id` integer NOT NULL,
    `repository_id` integer NOT NULL,
    UNIQUE (`tree_id`, `repository_id`)
)
;
ALTER TABLE `life_tree_repositories` ADD CONSTRAINT `repository_id_refs_id_34ffbf05` FOREIGN KEY (`repository_id`) REFERENCES `life_repository` (`id`);
### New Model: life.Tree
CREATE TABLE `life_tree` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `code` varchar(50) NOT NULL UNIQUE,
    `l10n_id` integer NOT NULL
)
;
ALTER TABLE `life_tree` ADD CONSTRAINT `l10n_id_refs_id_76dd734c` FOREIGN KEY (`l10n_id`) REFERENCES `life_forest` (`id`);
ALTER TABLE `life_tree_repositories` ADD CONSTRAINT `tree_id_refs_id_8a3a77d7` FOREIGN KEY (`tree_id`) REFERENCES `life_tree` (`id`);
### New Model: mbdb.Master
CREATE TABLE `mbdb_master` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
)
;
### New Model: mbdb.Slave
CREATE TABLE `mbdb_slave` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(150) NOT NULL UNIQUE
)
;
### New Model: mbdb.File
CREATE TABLE `mbdb_file` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `path` varchar(400) NOT NULL
)
;
ALTER TABLE `life_changeset_files` ADD CONSTRAINT `file_id_refs_id_71850ff9` FOREIGN KEY (`file_id`) REFERENCES `mbdb_file` (`id`);
### New Model: mbdb.Tag
CREATE TABLE `mbdb_tag` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `value` varchar(50) NOT NULL UNIQUE
)
;
### New Model: mbdb.Change_files
CREATE TABLE `mbdb_change_files` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `change_id` integer NOT NULL,
    `file_id` integer NOT NULL,
    UNIQUE (`change_id`, `file_id`)
)
;
ALTER TABLE `mbdb_change_files` ADD CONSTRAINT `file_id_refs_id_d2e8fad3` FOREIGN KEY (`file_id`) REFERENCES `mbdb_file` (`id`);
### New Model: mbdb.Change_tags
CREATE TABLE `mbdb_change_tags` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `change_id` integer NOT NULL,
    `tag_id` integer NOT NULL,
    UNIQUE (`change_id`, `tag_id`)
)
;
ALTER TABLE `mbdb_change_tags` ADD CONSTRAINT `tag_id_refs_id_9de48185` FOREIGN KEY (`tag_id`) REFERENCES `mbdb_tag` (`id`);
### New Model: mbdb.Change
CREATE TABLE `mbdb_change` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `number` integer UNSIGNED NOT NULL,
    `master_id` integer NOT NULL,
    `branch` varchar(100),
    `revision` varchar(50),
    `who` varchar(100),
    `comments` longtext,
    `when` datetime NOT NULL,
    UNIQUE (`number`, `master_id`)
)
;
ALTER TABLE `mbdb_change` ADD CONSTRAINT `master_id_refs_id_b9fb8de3` FOREIGN KEY (`master_id`) REFERENCES `mbdb_master` (`id`);
ALTER TABLE `mbdb_change_files` ADD CONSTRAINT `change_id_refs_id_dea72041` FOREIGN KEY (`change_id`) REFERENCES `mbdb_change` (`id`);
ALTER TABLE `mbdb_change_tags` ADD CONSTRAINT `change_id_refs_id_6aa2082e` FOREIGN KEY (`change_id`) REFERENCES `mbdb_change` (`id`);
### New Model: mbdb.SourceStamp
CREATE TABLE `mbdb_sourcestamp` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `branch` varchar(100),
    `revision` varchar(50)
)
;
### New Model: mbdb.NumberedChange
CREATE TABLE `mbdb_numberedchange` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `change_id` integer NOT NULL,
    `sourcestamp_id` integer NOT NULL,
    `number` integer NOT NULL
)
;
ALTER TABLE `mbdb_numberedchange` ADD CONSTRAINT `change_id_refs_id_b006de67` FOREIGN KEY (`change_id`) REFERENCES `mbdb_change` (`id`);
ALTER TABLE `mbdb_numberedchange` ADD CONSTRAINT `sourcestamp_id_refs_id_fa51598c` FOREIGN KEY (`sourcestamp_id`) REFERENCES `mbdb_sourcestamp` (`id`);
### New Model: mbdb.Property
CREATE TABLE `mbdb_property` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL,
    `source` varchar(20) NOT NULL,
    `value` longtext
)
;
### New Model: mbdb.Builder
CREATE TABLE `mbdb_builder` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `master_id` integer NOT NULL,
    `category` varchar(30),
    `bigState` varchar(30)
)
;
ALTER TABLE `mbdb_builder` ADD CONSTRAINT `master_id_refs_id_e7f56953` FOREIGN KEY (`master_id`) REFERENCES `mbdb_master` (`id`);
### New Model: mbdb.Build_properties
CREATE TABLE `mbdb_build_properties` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `build_id` integer NOT NULL,
    `property_id` integer NOT NULL,
    UNIQUE (`build_id`, `property_id`)
)
;
ALTER TABLE `mbdb_build_properties` ADD CONSTRAINT `property_id_refs_id_621d2a84` FOREIGN KEY (`property_id`) REFERENCES `mbdb_property` (`id`);
### New Model: mbdb.Build
CREATE TABLE `mbdb_build` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `buildnumber` integer,
    `builder_id` integer NOT NULL,
    `slave_id` integer,
    `starttime` datetime,
    `endtime` datetime,
    `result` smallint,
    `reason` varchar(50),
    `sourcestamp_id` integer
)
;
ALTER TABLE `mbdb_build` ADD CONSTRAINT `builder_id_refs_id_1cc1135a` FOREIGN KEY (`builder_id`) REFERENCES `mbdb_builder` (`id`);
ALTER TABLE `mbdb_build` ADD CONSTRAINT `slave_id_refs_id_55a9f17c` FOREIGN KEY (`slave_id`) REFERENCES `mbdb_slave` (`id`);
ALTER TABLE `mbdb_build` ADD CONSTRAINT `sourcestamp_id_refs_id_b49503ef` FOREIGN KEY (`sourcestamp_id`) REFERENCES `mbdb_sourcestamp` (`id`);
ALTER TABLE `mbdb_build_properties` ADD CONSTRAINT `build_id_refs_id_ff894e50` FOREIGN KEY (`build_id`) REFERENCES `mbdb_build` (`id`);
### New Model: mbdb.Step
CREATE TABLE `mbdb_step` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `text` longtext,
    `text2` longtext,
    `result` smallint,
    `starttime` datetime,
    `endtime` datetime,
    `build_id` integer NOT NULL
)
;
ALTER TABLE `mbdb_step` ADD CONSTRAINT `build_id_refs_id_9a45b8f6` FOREIGN KEY (`build_id`) REFERENCES `mbdb_build` (`id`);
### New Model: mbdb.URL
CREATE TABLE `mbdb_url` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL,
    `url` varchar(200) NOT NULL,
    `step_id` integer NOT NULL
)
;
ALTER TABLE `mbdb_url` ADD CONSTRAINT `step_id_refs_id_26565cb5` FOREIGN KEY (`step_id`) REFERENCES `mbdb_step` (`id`);
### New Model: mbdb.Log
CREATE TABLE `mbdb_log` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100),
    `filename` varchar(200) UNIQUE,
    `step_id` integer NOT NULL,
    `isFinished` bool NOT NULL,
    `html` longtext
)
;
ALTER TABLE `mbdb_log` ADD CONSTRAINT `step_id_refs_id_606ef278` FOREIGN KEY (`step_id`) REFERENCES `mbdb_step` (`id`);
### New Model: mbdb.BuildRequest_builds
CREATE TABLE `mbdb_buildrequest_builds` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `buildrequest_id` integer NOT NULL,
    `build_id` integer NOT NULL,
    UNIQUE (`buildrequest_id`, `build_id`)
)
;
ALTER TABLE `mbdb_buildrequest_builds` ADD CONSTRAINT `build_id_refs_id_f889be24` FOREIGN KEY (`build_id`) REFERENCES `mbdb_build` (`id`);
### New Model: mbdb.BuildRequest
CREATE TABLE `mbdb_buildrequest` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `builder_id` integer NOT NULL,
    `submitTime` datetime NOT NULL,
    `sourcestamp_id` integer NOT NULL
)
;
ALTER TABLE `mbdb_buildrequest` ADD CONSTRAINT `builder_id_refs_id_14179dde` FOREIGN KEY (`builder_id`) REFERENCES `mbdb_builder` (`id`);
ALTER TABLE `mbdb_buildrequest` ADD CONSTRAINT `sourcestamp_id_refs_id_47936487` FOREIGN KEY (`sourcestamp_id`) REFERENCES `mbdb_sourcestamp` (`id`);
ALTER TABLE `mbdb_buildrequest_builds` ADD CONSTRAINT `buildrequest_id_refs_id_17257334` FOREIGN KEY (`buildrequest_id`) REFERENCES `mbdb_buildrequest` (`id`);
### New Model: l10nstats.ModuleCount
CREATE TABLE `l10nstats_modulecount` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `count` integer NOT NULL
)
;
### New Model: l10nstats.Run_unchangedmodules
CREATE TABLE `l10nstats_run_unchangedmodules` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `run_id` integer NOT NULL,
    `modulecount_id` integer NOT NULL,
    UNIQUE (`run_id`, `modulecount_id`)
)
;
ALTER TABLE `l10nstats_run_unchangedmodules` ADD CONSTRAINT `modulecount_id_refs_id_370e3c93` FOREIGN KEY (`modulecount_id`) REFERENCES `l10nstats_modulecount` (`id`);
### New Model: l10nstats.Run_revisions
CREATE TABLE `l10nstats_run_revisions` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `run_id` integer NOT NULL,
    `changeset_id` integer NOT NULL,
    UNIQUE (`run_id`, `changeset_id`)
)
;
ALTER TABLE `l10nstats_run_revisions` ADD CONSTRAINT `changeset_id_refs_id_7b28c152` FOREIGN KEY (`changeset_id`) REFERENCES `life_changeset` (`id`);
### New Model: l10nstats.Run
CREATE TABLE `l10nstats_run` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `locale_id` integer NOT NULL,
    `tree_id` integer NOT NULL,
    `build_id` integer UNIQUE,
    `srctime` datetime,
    `missing` integer NOT NULL,
    `missingInFiles` integer NOT NULL,
    `obsolete` integer NOT NULL,
    `total` integer NOT NULL,
    `changed` integer NOT NULL,
    `unchanged` integer NOT NULL,
    `keys` integer NOT NULL,
    `errors` integer NOT NULL,
    `report` integer NOT NULL,
    `warnings` integer NOT NULL,
    `completion` smallint NOT NULL
)
;
ALTER TABLE `l10nstats_run` ADD CONSTRAINT `locale_id_refs_id_3aa0afc0` FOREIGN KEY (`locale_id`) REFERENCES `life_locale` (`id`);
ALTER TABLE `l10nstats_run` ADD CONSTRAINT `tree_id_refs_id_16c134d8` FOREIGN KEY (`tree_id`) REFERENCES `life_tree` (`id`);
ALTER TABLE `l10nstats_run` ADD CONSTRAINT `build_id_refs_id_dc954db4` FOREIGN KEY (`build_id`) REFERENCES `mbdb_build` (`id`);
ALTER TABLE `l10nstats_run_unchangedmodules` ADD CONSTRAINT `run_id_refs_id_b209049d` FOREIGN KEY (`run_id`) REFERENCES `l10nstats_run` (`id`);
ALTER TABLE `l10nstats_run_revisions` ADD CONSTRAINT `run_id_refs_id_b0b57a54` FOREIGN KEY (`run_id`) REFERENCES `l10nstats_run` (`id`);
### New Model: l10nstats.UnchangedInFile
CREATE TABLE `l10nstats_unchangedinfile` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `module` varchar(50) NOT NULL,
    `file` varchar(400) NOT NULL,
    `count` integer NOT NULL,
    `run_id` integer NOT NULL
)
;
ALTER TABLE `l10nstats_unchangedinfile` ADD CONSTRAINT `run_id_refs_id_6cacabfa` FOREIGN KEY (`run_id`) REFERENCES `l10nstats_run` (`id`);
### New Model: l10nstats.Active
CREATE TABLE `l10nstats_active` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `run_id` integer NOT NULL UNIQUE
)
;
ALTER TABLE `l10nstats_active` ADD CONSTRAINT `run_id_refs_id_6a924271` FOREIGN KEY (`run_id`) REFERENCES `l10nstats_run` (`id`);
### New Model: tinder.WebHead
CREATE TABLE `tinder_webhead` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL
)
;
### New Model: tinder.MasterMap
CREATE TABLE `tinder_mastermap` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `master_id` integer NOT NULL,
    `webhead_id` integer NOT NULL,
    `logmount` varchar(200) NOT NULL
)
;
ALTER TABLE `tinder_mastermap` ADD CONSTRAINT `master_id_refs_id_967c9f99` FOREIGN KEY (`master_id`) REFERENCES `mbdb_master` (`id`);
ALTER TABLE `tinder_mastermap` ADD CONSTRAINT `webhead_id_refs_id_1b192c5` FOREIGN KEY (`webhead_id`) REFERENCES `tinder_webhead` (`id`);
### New Model: shipping.Application
CREATE TABLE `shipping_application` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `code` varchar(30) NOT NULL
)
;
### New Model: shipping.AppVersion
CREATE TABLE `shipping_appversion` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `app_id` integer NOT NULL,
    `version` varchar(10) NOT NULL,
    `code` varchar(20) NOT NULL,
    `codename` varchar(30),
    `tree_id` integer NOT NULL
)
;
ALTER TABLE `shipping_appversion` ADD CONSTRAINT `app_id_refs_id_7d1eaa7b` FOREIGN KEY (`app_id`) REFERENCES `shipping_application` (`id`);
ALTER TABLE `shipping_appversion` ADD CONSTRAINT `tree_id_refs_id_49af3e12` FOREIGN KEY (`tree_id`) REFERENCES `life_tree` (`id`);
### New Model: shipping.Signoff
CREATE TABLE `shipping_signoff` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `push_id` integer NOT NULL,
    `appversion_id` integer NOT NULL,
    `author_id` integer NOT NULL,
    `when` datetime NOT NULL,
    `locale_id` integer NOT NULL
)
;
ALTER TABLE `shipping_signoff` ADD CONSTRAINT `push_id_refs_id_ac57f55e` FOREIGN KEY (`push_id`) REFERENCES `life_push` (`id`);
ALTER TABLE `shipping_signoff` ADD CONSTRAINT `appversion_id_refs_id_42fa1371` FOREIGN KEY (`appversion_id`) REFERENCES `shipping_appversion` (`id`);
ALTER TABLE `shipping_signoff` ADD CONSTRAINT `locale_id_refs_id_d4b18542` FOREIGN KEY (`locale_id`) REFERENCES `life_locale` (`id`);
ALTER TABLE `shipping_signoff` ADD CONSTRAINT `author_id_refs_id_18d006d1` FOREIGN KEY (`author_id`) REFERENCES `auth_user` (`id`);
### New Model: shipping.Action
CREATE TABLE `shipping_action` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `signoff_id` integer NOT NULL,
    `flag` integer NOT NULL,
    `author_id` integer NOT NULL,
    `when` datetime NOT NULL,
    `comment` longtext
)
;
ALTER TABLE `shipping_action` ADD CONSTRAINT `signoff_id_refs_id_eb5baa44` FOREIGN KEY (`signoff_id`) REFERENCES `shipping_signoff` (`id`);
ALTER TABLE `shipping_action` ADD CONSTRAINT `author_id_refs_id_e43c2378` FOREIGN KEY (`author_id`) REFERENCES `auth_user` (`id`);
### New Model: shipping.Snapshot
CREATE TABLE `shipping_snapshot` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `signoff_id` integer NOT NULL,
    `test` integer NOT NULL,
    `tid` integer NOT NULL
)
;
ALTER TABLE `shipping_snapshot` ADD CONSTRAINT `signoff_id_refs_id_9776e4f8` FOREIGN KEY (`signoff_id`) REFERENCES `shipping_signoff` (`id`);
### New Model: shipping.Milestone_signoffs
CREATE TABLE `shipping_milestone_signoffs` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `milestone_id` integer NOT NULL,
    `signoff_id` integer NOT NULL,
    UNIQUE (`milestone_id`, `signoff_id`)
)
;
ALTER TABLE `shipping_milestone_signoffs` ADD CONSTRAINT `signoff_id_refs_id_96184712` FOREIGN KEY (`signoff_id`) REFERENCES `shipping_signoff` (`id`);
### New Model: shipping.Milestone
CREATE TABLE `shipping_milestone` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `code` varchar(30) NOT NULL,
    `name` varchar(50) NOT NULL,
    `appver_id` integer NOT NULL,
    `status` integer NOT NULL
)
;
ALTER TABLE `shipping_milestone` ADD CONSTRAINT `appver_id_refs_id_7f9a7239` FOREIGN KEY (`appver_id`) REFERENCES `shipping_appversion` (`id`);
ALTER TABLE `shipping_milestone_signoffs` ADD CONSTRAINT `milestone_id_refs_id_14289ef4` FOREIGN KEY (`milestone_id`) REFERENCES `shipping_milestone` (`id`);
### New Model: shipping.Event
CREATE TABLE `shipping_event` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `type` integer NOT NULL,
    `date` date NOT NULL,
    `milestone_id` integer NOT NULL
)
;
ALTER TABLE `shipping_event` ADD CONSTRAINT `milestone_id_refs_id_f84768e7` FOREIGN KEY (`milestone_id`) REFERENCES `shipping_milestone` (`id`);
### New Model: webby.ProjectType
CREATE TABLE `webby_projecttype` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(80) NOT NULL
)
;
### New Model: webby.Project
CREATE TABLE `webby_project` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(80) NOT NULL,
    `slug` varchar(80) NOT NULL,
    `description` longtext NOT NULL,
    `verbatim_url` varchar(150),
    `l10n_repo_url` varchar(150),
    `code_repo_url` varchar(150),
    `stage_url` varchar(200),
    `final_url` varchar(200),
    `string_count` integer NOT NULL,
    `word_count` integer NOT NULL,
    `type_id` integer NOT NULL
)
;
ALTER TABLE `webby_project` ADD CONSTRAINT `type_id_refs_id_82d37d6d` FOREIGN KEY (`type_id`) REFERENCES `webby_projecttype` (`id`);
### New Model: webby.Weblocale
CREATE TABLE `webby_weblocale` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `project_id` integer NOT NULL,
    `locale_id` integer NOT NULL,
    `requestee_id` integer,
    `in_verbatim` bool NOT NULL,
    `in_vcs` bool NOT NULL,
    `is_on_stage` bool NOT NULL,
    `is_on_prod` bool NOT NULL,
    UNIQUE (`project_id`, `locale_id`)
)
;
ALTER TABLE `webby_weblocale` ADD CONSTRAINT `project_id_refs_id_eebc0b0a` FOREIGN KEY (`project_id`) REFERENCES `webby_project` (`id`);
ALTER TABLE `webby_weblocale` ADD CONSTRAINT `locale_id_refs_id_e6c68b2c` FOREIGN KEY (`locale_id`) REFERENCES `life_locale` (`id`);
ALTER TABLE `webby_weblocale` ADD CONSTRAINT `requestee_id_refs_id_ce716d21` FOREIGN KEY (`requestee_id`) REFERENCES `auth_user` (`id`);
CREATE INDEX `djcelery_periodictask_17d2d99d` ON `djcelery_periodictask` (`interval_id`);
CREATE INDEX `djcelery_periodictask_7aa5fda` ON `djcelery_periodictask` (`crontab_id`);
CREATE INDEX `djcelery_workerstate_eb8ac7e4` ON `djcelery_workerstate` (`last_heartbeat`);
CREATE INDEX `djcelery_taskstate_52094d6e` ON `djcelery_taskstate` (`name`);
CREATE INDEX `djcelery_taskstate_f0ba6500` ON `djcelery_taskstate` (`tstamp`);
CREATE INDEX `djcelery_taskstate_20fc5b84` ON `djcelery_taskstate` (`worker_id`);
CREATE INDEX `auth_permission_e4470c6e` ON `auth_permission` (`content_type_id`);
CREATE INDEX `auth_group_permissions_bda51c3c` ON `auth_group_permissions` (`group_id`);
CREATE INDEX `auth_group_permissions_1e014c8f` ON `auth_group_permissions` (`permission_id`);
CREATE INDEX `auth_user_user_permissions_fbfc09f1` ON `auth_user_user_permissions` (`user_id`);
CREATE INDEX `auth_user_user_permissions_1e014c8f` ON `auth_user_user_permissions` (`permission_id`);
CREATE INDEX `auth_user_groups_fbfc09f1` ON `auth_user_groups` (`user_id`);
CREATE INDEX `auth_user_groups_bda51c3c` ON `auth_user_groups` (`group_id`);
CREATE INDEX `auth_message_fbfc09f1` ON `auth_message` (`user_id`);
CREATE INDEX `django_session_c25c2c28` ON `django_session` (`expire_date`);
CREATE INDEX `django_admin_log_fbfc09f1` ON `django_admin_log` (`user_id`);
CREATE INDEX `django_admin_log_e4470c6e` ON `django_admin_log` (`content_type_id`);
CREATE INDEX `privacy_comment_e84fa2b0` ON `privacy_comment` (`policy_id`);
CREATE INDEX `privacy_comment_450e6bfb` ON `privacy_comment` (`who_id`);
CREATE INDEX `life_changeset_files_661cc59` ON `life_changeset_files` (`changeset_id`);
CREATE INDEX `life_changeset_files_2243e3be` ON `life_changeset_files` (`file_id`);
CREATE INDEX `life_changeset_parents_7584a7d7` ON `life_changeset_parents` (`from_changeset_id`);
CREATE INDEX `life_changeset_parents_ef353082` ON `life_changeset_parents` (`to_changeset_id`);
CREATE INDEX `life_changeset_b00d52be` ON `life_changeset` (`user`);
CREATE INDEX `life_changeset_d56253ba` ON `life_changeset` (`branch_id`);
CREATE INDEX `life_repository_changesets_6a730446` ON `life_repository_changesets` (`repository_id`);
CREATE INDEX `life_repository_changesets_661cc59` ON `life_repository_changesets` (`changeset_id`);
CREATE INDEX `life_repository_d4d59267` ON `life_repository` (`forest_id`);
CREATE INDEX `life_repository_5cee98e0` ON `life_repository` (`locale_id`);
CREATE INDEX `life_push_changesets_d39fc69c` ON `life_push_changesets` (`push_id`);
CREATE INDEX `life_push_changesets_661cc59` ON `life_push_changesets` (`changeset_id`);
CREATE INDEX `life_push_6a730446` ON `life_push` (`repository_id`);
CREATE INDEX `life_push_b00d52be` ON `life_push` (`user`);
CREATE INDEX `life_push_d3946b1b` ON `life_push` (`push_date`);
CREATE INDEX `life_tree_repositories_efd07f28` ON `life_tree_repositories` (`tree_id`);
CREATE INDEX `life_tree_repositories_6a730446` ON `life_tree_repositories` (`repository_id`);
CREATE INDEX `life_tree_582b5697` ON `life_tree` (`l10n_id`);
CREATE INDEX `mbdb_file_6a8a34e2` ON `mbdb_file` (`path`);
CREATE INDEX `mbdb_change_files_70799212` ON `mbdb_change_files` (`change_id`);
CREATE INDEX `mbdb_change_files_2243e3be` ON `mbdb_change_files` (`file_id`);
CREATE INDEX `mbdb_change_tags_70799212` ON `mbdb_change_tags` (`change_id`);
CREATE INDEX `mbdb_change_tags_3747b463` ON `mbdb_change_tags` (`tag_id`);
CREATE INDEX `mbdb_change_64d805fc` ON `mbdb_change` (`master_id`);
CREATE INDEX `mbdb_change_3419672c` ON `mbdb_change` (`who`);
CREATE INDEX `mbdb_numberedchange_70799212` ON `mbdb_numberedchange` (`change_id`);
CREATE INDEX `mbdb_numberedchange_98cd6059` ON `mbdb_numberedchange` (`sourcestamp_id`);
CREATE INDEX `mbdb_numberedchange_7c2dab66` ON `mbdb_numberedchange` (`number`);
CREATE INDEX `mbdb_property_52094d6e` ON `mbdb_property` (`name`);
CREATE INDEX `mbdb_property_48ee9dea` ON `mbdb_property` (`source`);
CREATE INDEX `mbdb_property_40858fbd` ON `mbdb_property` (`value`);
CREATE INDEX `mbdb_builder_64d805fc` ON `mbdb_builder` (`master_id`);
CREATE INDEX `mbdb_builder_34876983` ON `mbdb_builder` (`category`);
CREATE INDEX `mbdb_build_properties_f0e09603` ON `mbdb_build_properties` (`build_id`);
CREATE INDEX `mbdb_build_properties_6a812853` ON `mbdb_build_properties` (`property_id`);
CREATE INDEX `mbdb_build_4a03d4ed` ON `mbdb_build` (`buildnumber`);
CREATE INDEX `mbdb_build_369e889a` ON `mbdb_build` (`builder_id`);
CREATE INDEX `mbdb_build_9ab85824` ON `mbdb_build` (`slave_id`);
CREATE INDEX `mbdb_build_98cd6059` ON `mbdb_build` (`sourcestamp_id`);
CREATE INDEX `mbdb_step_f0e09603` ON `mbdb_step` (`build_id`);
CREATE INDEX `mbdb_url_ef86119e` ON `mbdb_url` (`step_id`);
CREATE INDEX `mbdb_log_ef86119e` ON `mbdb_log` (`step_id`);
CREATE INDEX `mbdb_buildrequest_builds_181e19c9` ON `mbdb_buildrequest_builds` (`buildrequest_id`);
CREATE INDEX `mbdb_buildrequest_builds_f0e09603` ON `mbdb_buildrequest_builds` (`build_id`);
CREATE INDEX `mbdb_buildrequest_369e889a` ON `mbdb_buildrequest` (`builder_id`);
CREATE INDEX `mbdb_buildrequest_98cd6059` ON `mbdb_buildrequest` (`sourcestamp_id`);
CREATE INDEX `l10nstats_run_unchangedmodules_bc73c538` ON `l10nstats_run_unchangedmodules` (`run_id`);
CREATE INDEX `l10nstats_run_unchangedmodules_2105bafe` ON `l10nstats_run_unchangedmodules` (`modulecount_id`);
CREATE INDEX `l10nstats_run_revisions_bc73c538` ON `l10nstats_run_revisions` (`run_id`);
CREATE INDEX `l10nstats_run_revisions_661cc59` ON `l10nstats_run_revisions` (`changeset_id`);
CREATE INDEX `l10nstats_run_5cee98e0` ON `l10nstats_run` (`locale_id`);
CREATE INDEX `l10nstats_run_efd07f28` ON `l10nstats_run` (`tree_id`);
CREATE INDEX `l10nstats_run_b9d3dca7` ON `l10nstats_run` (`srctime`);
CREATE INDEX `l10nstats_unchangedinfile_ae49275d` ON `l10nstats_unchangedinfile` (`module`);
CREATE INDEX `l10nstats_unchangedinfile_6e62a245` ON `l10nstats_unchangedinfile` (`file`);
CREATE INDEX `l10nstats_unchangedinfile_516bb1bd` ON `l10nstats_unchangedinfile` (`count`);
CREATE INDEX `l10nstats_unchangedinfile_bc73c538` ON `l10nstats_unchangedinfile` (`run_id`);
CREATE INDEX `tinder_mastermap_64d805fc` ON `tinder_mastermap` (`master_id`);
CREATE INDEX `tinder_mastermap_272ec299` ON `tinder_mastermap` (`webhead_id`);
CREATE INDEX `shipping_appversion_269da59a` ON `shipping_appversion` (`app_id`);
CREATE INDEX `shipping_appversion_efd07f28` ON `shipping_appversion` (`tree_id`);
CREATE INDEX `shipping_signoff_d39fc69c` ON `shipping_signoff` (`push_id`);
CREATE INDEX `shipping_signoff_3d278d29` ON `shipping_signoff` (`appversion_id`);
CREATE INDEX `shipping_signoff_cc846901` ON `shipping_signoff` (`author_id`);
CREATE INDEX `shipping_signoff_5cee98e0` ON `shipping_signoff` (`locale_id`);
CREATE INDEX `shipping_action_b227804b` ON `shipping_action` (`signoff_id`);
CREATE INDEX `shipping_action_cc846901` ON `shipping_action` (`author_id`);
CREATE INDEX `shipping_snapshot_b227804b` ON `shipping_snapshot` (`signoff_id`);
CREATE INDEX `shipping_milestone_signoffs_9cfa291f` ON `shipping_milestone_signoffs` (`milestone_id`);
CREATE INDEX `shipping_milestone_signoffs_b227804b` ON `shipping_milestone_signoffs` (`signoff_id`);
CREATE INDEX `shipping_milestone_6e5ef8fa` ON `shipping_milestone` (`appver_id`);
CREATE INDEX `shipping_event_9cfa291f` ON `shipping_event` (`milestone_id`);
CREATE INDEX `webby_project_a951d5d6` ON `webby_project` (`slug`);
CREATE INDEX `webby_project_777d41c8` ON `webby_project` (`type_id`);
CREATE INDEX `webby_weblocale_b6620684` ON `webby_weblocale` (`project_id`);
CREATE INDEX `webby_weblocale_5cee98e0` ON `webby_weblocale` (`locale_id`);
CREATE INDEX `webby_weblocale_2e176808` ON `webby_weblocale` (`requestee_id`);
