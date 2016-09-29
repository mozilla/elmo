# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import datetime
from nose.tools import eq_, ok_
from django.test import TestCase
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
        ok_(not form.is_valid())

        form = SignoffFilterForm({
          'av': '',
          'up_until': '',
        })
        ok_(not form.is_valid())

        # check a couple of recognized recognized up_until values
        form = SignoffFilterForm({
          'up_until': '2012-08-17 14:50:00',
        })
        ok_(not form.is_valid())

        eq_(form.cleaned_data['up_until'],
            datetime.datetime(2012, 8, 17, 14, 50, 0))

        # not a valid date
        form = SignoffFilterForm({
          'up_until': '2012-02-32 14:50:00',
        })
        ok_(not form.is_valid())
        ok_(form.errors)
        ok_('up_until' in form.errors)

        # try passing an AppVersion
        # ...left blank
        form = SignoffFilterForm({
          'av': '',
        })
        ok_(not form.is_valid())

        # ...that doesn't exist
        form = SignoffFilterForm({
          'av': 'xxx',
        })
        ok_(not form.is_valid())
        ok_(form.errors)
        ok_('av' in form.errors)

        # ...that does exist
        form = SignoffFilterForm({
          'av': self.appver.code,
        })
        ok_(form.is_valid())
