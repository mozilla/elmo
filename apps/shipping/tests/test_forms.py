# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from elmo.test import TestCase
from shipping.forms import SignoffFilterForm
from life.models import Tree, Forest
from shipping.models import AppVersion, Application


class FormTests(TestCase):

    def setUp(self):
        self.app = Application.objects.create(
          name='firefox',
          code='fx'
        )
        l10n = Forest.objects.create(
          name='l10n-central',
          url='http://hg.mozilla.org/l10n-central/',
        )
        tree = Tree.objects.create(
          code='fx',
          l10n=l10n,
        )
        self.appver = AppVersion.objects.create(
          app=self.app,
          version='1',
          code='fx1',
          codename='foxy'
        )
        self.appver.trees.through.objects.create(
            tree=tree,
            appversion=self.appver,
            start=None,
            end=None
        )

    def test_signoff_filter_form(self):
        form = SignoffFilterForm({})
        self.assertFalse(form.is_valid())

        form = SignoffFilterForm({
          'av': '',
          'up_until': '',
        })
        self.assertFalse(form.is_valid())

        # check a couple of recognized recognized up_until values
        form = SignoffFilterForm({
          'up_until': '2012-08-17 14:50:00',
        })
        self.assertFalse(form.is_valid())

        self.assertEqual(
            form.cleaned_data['up_until'],
            datetime.datetime(2012, 8, 17, 14, 50, 0))

        # not a valid date
        form = SignoffFilterForm({
          'up_until': '2012-02-32 14:50:00',
        })
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)
        self.assertIn('up_until', form.errors)

        # try passing an AppVersion
        # ...left blank
        form = SignoffFilterForm({
          'av': '',
        })
        self.assertFalse(form.is_valid())

        # ...that doesn't exist
        form = SignoffFilterForm({
          'av': 'xxx',
        })
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)
        self.assertIn('av', form.errors)

        # ...that does exist
        form = SignoffFilterForm({
          'av': self.appver.code,
        })
        self.assertTrue(form.is_valid())
