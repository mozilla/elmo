# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#    Peter Bengtsson <peterbe@mozilla.com>
#    Axel Hecht <l10n@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Tests for the shipping.
'''
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from shipping.models import Milestone, Application, AppVersion, Signoff, Action
from shipping.views import _signoffs
from life.models import Tree, Forest, Locale
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType


class ShippingTestCase(TestCase):

    def _create_appver_milestone(self):
        app = Application.objects.create(
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
        appver = AppVersion.objects.create(
          app=app,
          version='1',
          code='fx1',
          codename='foxy',
          tree=tree,
        )
        milestone = Milestone.objects.create(
          code='one',
          name='One',
          appver=appver,
        )

        return appver, milestone

    def test_dashboard_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.dashboard')
        # Fail
        response = self.client.get(url, dict(av="junk"))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url, dict(ms="junk"))
        self.assertEqual(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()

        # Succeed
        response = self.client.get(url, dict(ms=milestone.code))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        self.assertEqual(response.status_code, 200)

    def test_l10n_changesets_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.l10n_changesets')
        # Fail
        response = self.client.get(url, dict(ms=""))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        self.assertEqual(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        self.assertEqual(response.status_code, 200)

    def test_shipped_locales_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.shipped_locales')
        # Fail
        response = self.client.get(url, dict(ms=""))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        self.assertEqual(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        self.assertEqual(response.status_code, 200)

    def test_signoff_json_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.signoff_json')
        # Fail
        response = self.client.get(url, dict(ms=""))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        self.assertEqual(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        self.assertEqual(response.status_code, 200)

    def test_confirm_ship_mstone_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.confirm_ship_mstone')
        # Fail
        response = self.client.get(url, dict(ms="junk"))
        self.assertEqual(response.status_code, 404)

        # Succeed
        __, milestone = self._create_appver_milestone()
        milestone.status = 1
        milestone.save()
        response = self.client.get(url, dict(ms=milestone.code))
        self.assertEqual(response.status_code, 200)

    def test_ship_mstone_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.ship_mstone')
        # Fail
        response = self.client.get(url, dict(ms="junk"))
        self.assertEqual(response.status_code, 405)
        response = self.client.post(url, dict(ms="junk"))
        # redirects because we're not logged and don't have the permission
        self.assertEqual(response.status_code, 302)

        milestone_content_type, __ = ContentType.objects.get_or_create(
          name='milestone',
        )
        perm, __ = Permission.objects.get_or_create(
          name='Can ship a Milestone',
          content_type=milestone_content_type,
          codename='can_ship'
        )
        admin = User.objects.create(
          username='admin',
        )
        admin.set_password('secret')
        admin.user_permissions.add(perm)
        admin.save()
        assert self.client.login(username='admin', password='secret')

        __, milestone = self._create_appver_milestone()
        response = self.client.post(url, dict(ms="junk"))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(url, dict(ms=milestone.code))
        self.assertEqual(response.status_code, 302)

        milestone = Milestone.objects.get(code=milestone.code)
        self.assertEqual(milestone.status, 2)


class SignOffTest(TestCase):
    fixtures = ["test_repos.json", "test_pushes.json", "signoffs.json"]

    def setUp(self):
        self.av = AppVersion.objects.get(code="fx1.0")

    def test_count(self):
        """Test that we have the right amount of Signoffs and Actions"""
        self.assertEqual(Signoff.objects.count(), 2)
        self.assertEqual(Action.objects.count(), 3)

    def test_accepted(self):
        """Test for the german accepted signoff"""
        so = _signoffs(self.av, locale="de")
        self.assertEqual(so.push.tip.shortrev, "l10n de 0002")
        self.assertEqual(so.locale.code, "de")
        self.assertEqual(so.action_set.count(), 2)

    def test_pending(self):
        """Test for the pending polish signoff"""
        so = _signoffs(self.av, status=0, locale="pl")
        self.assertEqual(so.push.tip.shortrev, "l10n pl 0003")
        self.assertEqual(so.locale.code, "pl")
        self.assertEqual(so.action_set.count(), 1)

    def test_getlist(self):
        """Test that the list returns on accepted and one pending signoff."""
        sos = _signoffs(self.av, getlist=True)
        self.assertEqual(sos, {("fx", "pl"): [0], ("fx", "de"): [1]})
