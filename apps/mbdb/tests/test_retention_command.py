# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Unit testing for the build-retention command.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import os
import shutil
import tempfile
from six.moves import StringIO
from elmo.test import TestCase
from django.core import management
from django.test import override_settings
from mbdb.models import Log, Step, Build, Builder, Main, Subordinate


class CommandTest(TestCase):

    def setUp(self):
        super(CommandTest, self).setUp()
        self.now = datetime.datetime.utcnow()
        self.buildsdir = tempfile.mkdtemp()
        self.main = Main.objects.create(
         name='head',
        )
        self.builder = Builder.objects.create(
          name='builder1',
          main=self.main,
        )
        self.subordinate = Subordinate.objects.create(
          name='subordinate 1',
        )

    def tearDown(self):
        shutil.rmtree(self.buildsdir)

    def build_for(self, timestamp):
        if not os.path.exists(os.path.join(self.buildsdir, self.builder.name)):
            os.makedirs(os.path.join(self.buildsdir, self.builder.name))
        try:
            last_build = self.builder.builds.order_by('-buildnumber')[0]
            buildnumber = last_build.buildnumber + 1
        except IndexError:
            buildnumber = 1
        build = self.builder.builds.create(
          buildnumber=buildnumber,
          subordinate=self.subordinate,
          starttime=timestamp - datetime.timedelta(seconds=1),
          endtime=timestamp,
          result=1,
        )
        builder_pickle_mock = os.path.join(
            self.buildsdir, self.builder.name, str(buildnumber)
        )
        logs = []
        with open(builder_pickle_mock, 'w'):
            pass
        self.assertTrue(os.path.isfile(builder_pickle_mock))
        step = build.steps.create(
          name='step_1',
          starttime=timestamp - datetime.timedelta(seconds=1),
          endtime=timestamp,
        )
        log = step.logs.create(
            name='stdio',
            filename='{}/{}-{}-{}'.format(
                self.builder.name,
                build.buildnumber,
                step.name,
                'stdio',
            ),
            isFinished=True
        )
        logs.append(os.path.join(self.buildsdir, log.filename))
        with open(logs[-1], 'w'):
            pass
        self.assertTrue(os.path.isfile(logs[-1]))
        step = build.steps.create(
          name='step_2',
          starttime=timestamp - datetime.timedelta(seconds=1),
          endtime=timestamp,
        )
        log = step.logs.create(
            name='stdio',
            filename='{}/{}-{}-{}'.format(
                self.builder.name,
                build.buildnumber,
                step.name,
                'stdio',
            ),
            isFinished=True
        )
        logs.append(os.path.join(self.buildsdir, log.filename + '.bz2'))
        with open(logs[-1], 'w'):
            pass
        self.assertTrue(os.path.isfile(logs[-1]))
        step.logs.create(
            name='err.html',
            filename=None,
            html='<div>some html</div>',
            isFinished=True
        )
        return builder_pickle_mock, logs

    def test_empty_command(self):
        out = StringIO()
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command('build-retention', stdout=out)
        self.assertEqual(Build.objects.count(), 0)
        self.assertEqual(Step.objects.count(), 0)
        self.assertEqual(Log.objects.count(), 0)

    def test_command_with_old_build(self):
        '''One Build is two days old, logs, steps, and builder pickle
        should be removed.
        There's also a recent build, which should get not touched at all.
        '''
        out = StringIO()
        # old build
        b1, logs1 = self.build_for(self.now - datetime.timedelta(days=2))
        # new build
        b2, logs2 = self.build_for(self.now - datetime.timedelta(days=.5))
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command(
                'build-retention', '-W',
                '--builds-before=3', '--logs-before=3',
                stdout=out
            )
        self.assertTrue(os.path.isfile(b1))
        self.assertTrue(all(os.path.isfile(l) for l in logs1))
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))

        # dry run, first
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command(
                'build-retention', '-W',
                '--dry-run',
                stdout=out
            )
        self.assertTrue(os.path.isfile(b1))
        self.assertTrue(all(os.path.isfile(l) for l in logs1))
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))

        # Now wet run, actually delete files for b2.
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command('build-retention', '-W', stdout=out)
        self.assertFalse(os.path.isfile(b1))
        self.assertTrue(all(not os.path.isfile(l) for l in logs1))
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))
        # We kept the new build and its steps and logs are gone.
        self.assertEqual(Build.objects.count(), 1)
        self.assertEqual(Step.objects.count(), 2)
        self.assertEqual(Log.objects.count(), 3)
        # Run it again, so we validate that we're idempotent
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command('build-retention', '-W', stdout=out)
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))
        self.assertEqual(Build.objects.count(), 1)
        self.assertEqual(Step.objects.count(), 2)
        self.assertEqual(Log.objects.count(), 3)

    def test_command_with_missing_build_pickle(self):
        '''One Build is two days old, logs, steps, and builder pickle
        should be removed.
        The builder pickle is missing, which causes errors to be raised.
        There's also a recent build, which should get not touched at all.
        '''
        out = StringIO()
        # old build
        b1, logs1 = self.build_for(self.now - datetime.timedelta(days=2))
        # new build
        b2, logs2 = self.build_for(self.now - datetime.timedelta(days=.5))

        # remove the build file
        os.remove(b1)

        # dry run, first
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            with self.assertRaises(management.CommandError):
                management.call_command(
                    'build-retention', '-W',
                    '--dry-run',
                    stdout=out
                )
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command(
                'build-retention',
                '--dry-run',
                stdout=out
            )
        self.assertFalse(os.path.isfile(b1))
        self.assertTrue(all(os.path.isfile(l) for l in logs1))
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))

        # Now wet run, actually delete files for b2.
        # With warnings first, fail, and then w/out warnings
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            with self.assertRaises(management.CommandError):
                management.call_command('build-retention', '-W', stdout=out)
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command('build-retention', stdout=out)
        self.assertFalse(os.path.isfile(b1))
        self.assertTrue(all(not os.path.isfile(l) for l in logs1))
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))
        # We kept the new build and its steps and logs are gone.
        self.assertEqual(Build.objects.count(), 1)
        self.assertEqual(Step.objects.count(), 2)
        self.assertEqual(Log.objects.count(), 3)

    def test_command_with_missing_log_file(self):
        '''One Build is two days old, logs, steps, and builder pickle
        should be removed.
        One log file is missing, which causes errors to be raised.
        There's also a recent build, which should get not touched at all.
        '''
        out = StringIO()
        # old build
        b1, logs1 = self.build_for(self.now - datetime.timedelta(days=2))
        # new build
        b2, logs2 = self.build_for(self.now - datetime.timedelta(days=.5))

        # remove a log file
        os.remove(logs1.pop(1))

        # dry run, first
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            with self.assertRaises(management.CommandError):
                management.call_command(
                    'build-retention', '-W',
                    '--dry-run',
                    stdout=out
                )
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command(
                'build-retention',
                '--dry-run',
                stdout=out
            )
        self.assertTrue(os.path.isfile(b1))
        self.assertTrue(all(os.path.isfile(l) for l in logs1))
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))

        # Now wet run, actually delete files for b2.
        # With warnings first, fail, and then w/out warnings
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            with self.assertRaises(management.CommandError):
                management.call_command('build-retention', '-W', stdout=out)
        with override_settings(LOG_MOUNTS={self.main.name: self.buildsdir}):
            management.call_command('build-retention', stdout=out)
        self.assertFalse(os.path.isfile(b1))
        self.assertTrue(all(not os.path.isfile(l) for l in logs1))
        self.assertTrue(os.path.isfile(b2))
        self.assertTrue(all(os.path.isfile(l) for l in logs2))
        # We kept the new build and its steps and logs are gone.
        self.assertEqual(Build.objects.count(), 1)
        self.assertEqual(Step.objects.count(), 2)
        self.assertEqual(Log.objects.count(), 3)
