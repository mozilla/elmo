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
import six
from six.moves import StringIO
from elmo.test import TestCase
from django.core import management
from django.test import override_settings
from mbdb.models import Property, Step, Build, Builder, Master, Slave


class CommandTest(TestCase):

    def setUp(self):
        super(CommandTest, self).setUp()
        self.now = datetime.datetime.utcnow()
        self.buildsdir = tempfile.mkdtemp()
        self.master = Master.objects.create(
         name='head',
        )
        self.builder = Builder.objects.create(
          name='builder1',
          master=self.master,
        )
        self.slave = Slave.objects.create(
          name='slave 1',
        )

    def tearDown(self):
        shutil.rmtree(self.buildsdir)

    def build_for(self, timestamp):
        os.makedirs(os.path.join(self.buildsdir, self.builder.name))
        try:
            buildnumber = self.builder.builds.order_by('-buildnumber')[0] + 1
        except IndexError:
            buildnumber = 1
        build = self.builder.builds.create(
          buildnumber=buildnumber,
          slave=self.slave,
          starttime=timestamp - datetime.timedelta(seconds=1),
          endtime=timestamp,
          result=1,
        )
        open(os.path.join(self.buildsdir, self.builder.name, str(buildnumber)), 'w')
        self.assertTrue(os.path.isfile(os.path.join(self.buildsdir, self.builder.name, str(buildnumber))))
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
        open(os.path.join(self.buildsdir, log.filename), 'w')
        self.assertTrue(os.path.isfile(os.path.join(self.buildsdir, log.filename)))

    def test_empty_command(self):
        out = StringIO()
        with override_settings(LOG_MOUNTS={self.master.name: self.buildsdir}):
            management.call_command('build-retention', stdout=out)

    def test_command_with_one_old_build(self):
        '''Build is two days old, log should be removed, builder pickle not.
        '''
        out = StringIO()
        self.build_for(self.now - datetime.timedelta(days=2))
        with override_settings(LOG_MOUNTS={self.master.name: self.buildsdir}):
            management.call_command(
                'build-retention', '-W', '--builds-before=3', '--logs-before=3',
                stdout=out
            )
        self.assertTrue(os.path.isfile(os.path.join(
            self.buildsdir,
            self.builder.name,
            '1'
        )))
        self.assertTrue(os.path.isfile(os.path.join(
            self.buildsdir,
            self.builder.name,
            '1-step_1-stdio'
        )))
        with override_settings(LOG_MOUNTS={self.master.name: self.buildsdir}):
            management.call_command('build-retention', '-W', stdout=out)
        self.assertTrue(os.path.isfile(os.path.join(
            self.buildsdir,
            self.builder.name,
            '1'
        )))
        self.assertFalse(os.path.isfile(os.path.join(
            self.buildsdir,
            self.builder.name,
            '1-step_1-stdio'
        )))
