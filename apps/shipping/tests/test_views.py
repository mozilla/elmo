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

import re
from urlparse import urlparse
from nose.tools import eq_, ok_
#from django.test import TestCase
from test_utils import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson as json
from l10nstats.models import Run
from commons.tests.mixins import EmbedsTestCaseMixin
from life.models import Tree, Forest, Locale
from shipping.models import Milestone, Application, AppVersion


class ShippingTestCaseBase(TestCase, EmbedsTestCaseMixin):

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


class ShippingTestCase(ShippingTestCaseBase):

    def test_basic_render_index_page(self):
        """render the shipping index page"""
        url = reverse('shipping.views.index')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_basic_render_app_changes(self):
        """render shipping.views.app.changes"""
        url = reverse('shipping.views.app.changes',
                      args=['junk'])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        appver, milestone = self._create_appver_milestone()
        url = reverse('shipping.views.app.changes',
                      args=[appver.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_('<title>Locale changes for %s' % appver in response.content)
        ok_('<h1>Locale changes for %s' % appver in response.content)

    def test_basic_render_confirm_drill_mstone(self):
        """render shipping.views.confirm_drill_mstone"""
        url = reverse('shipping.views.confirm_drill_mstone')
        response = self.client.get(url)
        eq_(response.status_code, 404)
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302)  # not permission to view

        admin = User.objects.create_user(
          username='admin',
          email='admin@mozilla.com',
          password='secret',
        )
        admin.user_permissions.add(
          Permission.objects.get(codename='can_ship')
        )
        assert self.client.login(username='admin', password='secret')
        response = self.client.get(url, {'ms': 'junk'})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302)

        milestone.status = 1
        milestone.save()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 200)

        self.assert_all_embeds(response.content)
        ok_('<title>Shipping %s' % milestone in response.content)
        ok_('<h1>Shipping %s' % milestone in response.content)

    def test_basic_render_confirm_ship_mstone(self):
        """render shipping.views.confirm_ship_mstone"""
        url = reverse('shipping.views.confirm_ship_mstone')
        response = self.client.get(url)
        eq_(response.status_code, 404)
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302)  # not permission to view

        # Note how confirm doesn't require the 'can_ship' permission even
        # though the POST to actually ship does require the permission. The
        # reason for this is because the confirmation page has been used to
        # summorize what can be shipped and this URL is shared with people
        # outside this permission.
        # In fact, you don't even need to be logged in.

        response = self.client.get(url, {'ms': 'junk'})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302)

        milestone.status = 1
        milestone.save()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 200)

        self.assert_all_embeds(response.content)
        ok_('<title>Shipping %s' % milestone in response.content)
        ok_('<h1>Shipping %s' % milestone in response.content)

    def test_dashboard_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.dashboard')
        # Fail
        response = self.client.get(url, dict(av="junk"))
        eq_(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()

        # Succeed
        response = self.client.get(url, dict(av=appver.code))
        eq_(response.status_code, 200)

    def test_l10n_changesets_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.status.l10n_changesets')
        # Fail
        response = self.client.get(url, dict(ms=""))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        eq_(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        eq_(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        eq_(response.status_code, 200)

    def test_shipped_locales_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.status.shipped_locales')
        # Fail
        response = self.client.get(url, dict(ms=""))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        eq_(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        eq_(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        eq_(response.status_code, 200)

    def test_confirm_ship_mstone_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.confirm_ship_mstone')

        admin = User.objects.create_user(
          username='admin',
          email='admin@mozilla.com',
          password='secret',
        )
        admin.user_permissions.add(
          Permission.objects.get(codename='can_ship')
        )
        assert self.client.login(username='admin', password='secret')

        # Fail
        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)

        # Succeed
        __, milestone = self._create_appver_milestone()
        milestone.status = 1
        milestone.save()
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)

    def test_ship_mstone_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.ship_mstone')
        # Fail
        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 405)
        response = self.client.post(url, dict(ms="junk"))
        # redirects because we're not logged and don't have the permission
        eq_(response.status_code, 302)

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
        eq_(response.status_code, 404)

        milestone.status = Milestone.OPEN
        milestone.save()
        response = self.client.post(url, dict(ms=milestone.code))
        eq_(response.status_code, 302)

        milestone = Milestone.objects.get(code=milestone.code)
        eq_(milestone.status, 2)

    def test_milestones_static_files(self):
        """render the milestones page and check all static files"""
        url = reverse('shipping.views.milestones')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_about_milestone_static_files(self):
        """render the about milestone page and check all static files"""
        url = reverse('shipping.views.milestone.about',
                      args=['junk'])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        __, milestone = self._create_appver_milestone()
        url = reverse('shipping.views.milestone.about',
                      args=[milestone.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_legacy_redirect_about_milestone(self):
        """calling the dashboard with a 'ms' parameter (which is or is not a
        valid Milestone) should redirect to the about milestone page instead.
        """
        url = reverse('shipping.views.dashboard')
        response = self.client.get(url, {'ms': 'anything'})
        eq_(response.status_code, 302)
        url = reverse('shipping.views.milestone.about',
                      args=['anything'])
        eq_(urlparse(response['location']).path, url)

    def test_status_json_basic(self):
        url = reverse('shipping.views.status.status_json')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(struct['items'], [])

        appver, milestone = self._create_appver_milestone()
        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        run = Run.objects.create(
          tree=appver.tree,
          locale=locale,
        )
        assert Run.objects.all()
        run.activate()
        assert Run.objects.filter(active__isnull=False)
        response = self.client.get(url)
        struct = json.loads(response.content)
        ok_(struct['items'])

    def test_status_json_by_treeless_appversion(self):
        url = reverse('shipping.views.status.status_json')
        appver, milestone = self._create_appver_milestone()
        appver.tree = None
        appver.save()
        response = self.client.get(url, {'av': appver.code})

        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(struct['items'], [])

    def test_status_json_multiple_locales_multiple_trees(self):
        url = reverse('shipping.views.status.status_json')

        appver, milestone = self._create_appver_milestone()
        locale_en, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        locale_ro, __ = Locale.objects.get_or_create(
          code='ro',
          name='Romanian',
        )
        locale_ta, __ = Locale.objects.get_or_create(
          code='ta',
          name='Tamil',
        )

        # 4 trees
        tree, = Tree.objects.all()
        tree2 = Tree.objects.create(
          code='fy',
          l10n=tree.l10n,
        )
        tree3 = Tree.objects.create(
          code='fz',
          l10n=tree.l10n,
        )
        # this tree won't correspond to a AppVersion
        tree4 = Tree.objects.create(
          code='tree-loner',
          l10n=tree.l10n,
        )
        assert Tree.objects.count() == 4

        # 4 appversions
        appver2 = AppVersion.objects.create(
          app=appver.app,
          code='FY1',
          tree=tree2
        )
        appver3 = AppVersion.objects.create(
          app=appver.app,
          code='FZ1',
          tree=tree3
        )
        AppVersion.objects.create(
          app=appver.app,
          code='F-LONER',
        )

        assert AppVersion.objects.count() == 4

        data = {}  # All!
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        appver4trees = [x for x in struct['items']
                        if x['type'] == 'AppVer4Tree']

        trees = [x['label'] for x in appver4trees]
        # note that trees without an appversion isn't returned
        eq_(trees, [tree.code, tree2.code, tree3.code])
        appversions = [x['appversion'] for x in appver4trees]
        # note that appversion without an appversion isn't returned
        eq_(appversions, [appver.code, appver2.code, appver3.code])

        # query a specific set of trees
        data = {'tree': [tree2.code, tree3.code]}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        appver4trees = [x for x in struct['items']
                        if x['type'] == 'AppVer4Tree']
        trees = [x['label'] for x in appver4trees]
        eq_(trees, [tree.code, tree2.code, tree3.code])

        # query a specific set of trees, one which isn't implemented by any
        # appversion
        data = {'tree': [tree3.code, tree4.code]}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        appver4trees = [x for x in struct['items']
                        if x['type'] == 'AppVer4Tree']
        trees = [x['label'] for x in appver4trees]
        # tree4 is skipped because there's no appversion for that one
        assert not Run.objects.all()
        eq_(trees, [tree.code, tree2.code, tree3.code])

        # Now, let's add some Runs
        run = Run.objects.create(
          tree=tree,
          locale=locale_en,
        )
        run.activate()
        data = {}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        ok_(struct['items'])
        builds = [x for x in struct['items'] if x['type'] == 'Build']
        eq_(builds[0]['runid'], run.pk)

        data = {'tree': tree2.code}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        builds = [x for x in struct['items'] if x['type'] == 'Build']
        eq_(builds, [])

        data = {'tree': tree.code, 'locale': locale_ta.code}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        builds = [x for x in struct['items'] if x['type'] == 'Build']
        eq_(builds, [])

        data = {'tree': tree.code, 'locale': locale_en.code}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        builds = [x for x in struct['items'] if x['type'] == 'Build']
        eq_(builds[0]['runid'], run.pk)

        # doing data={'tree': tree2.code} excludes the run I have but setting
        # a AppVersion that points to the right tree should include it
        data = {'tree': tree2.code, 'av': appver.code}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        builds = [x for x in struct['items'] if x['type'] == 'Build']
        eq_(builds[0]['runid'], run.pk)

        # but if you specify a locale it gets filtered out
        data = {'av': appver.code, 'locale': locale_ta.code}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        builds = [x for x in struct['items'] if x['type'] == 'Build']
        eq_(builds, [])

        run.locale = locale_ta
        run.save()
        data = {'av': appver.code, 'locale': locale_ta.code}
        response = self.client.get(url, data)
        struct = json.loads(response.content)
        builds = [x for x in struct['items'] if x['type'] == 'Build']
        eq_(builds[0]['runid'], run.pk)

    def test_dashboard_locales_trees_av_query_generator(self):
        """the dashboard view takes request.GET parameters, massages them and
        turn them into a query string that gets passed to the JSON view later.
        """
        url = reverse('shipping.views.dashboard')
        response = self.client.get(url, {'locale': 'xxx'})
        eq_(response.status_code, 404)
        response = self.client.get(url, {'tree': 'xxx'})
        eq_(response.status_code, 404)
        response = self.client.get(url, {'av': 'xxx'})
        eq_(response.status_code, 404)

        def get_query(content):
            json_url = reverse('shipping.views.status.status_json')
            return re.findall('href="%s\?([^"]*)"' % json_url, content)[0]

        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(get_query(response.content), '')

        Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )

        response = self.client.get(url, {'locale': 'en-US'})
        eq_(response.status_code, 200)
        eq_(get_query(response.content), 'locale=en-US')

        response = self.client.get(url, {'locale': ['en-US', 'xxx']})
        eq_(response.status_code, 404)

        Locale.objects.get_or_create(
          code='ta',
          name='Tamil',
        )
        response = self.client.get(url, {'locale': ['en-US', 'ta']})
        eq_(response.status_code, 200)
        eq_(get_query(response.content), 'locale=en-US&locale=ta')

        appver, __ = self._create_appver_milestone()
        tree, = Tree.objects.all()
        response = self.client.get(url, {'tree': tree.code})
        eq_(response.status_code, 200)
        eq_(get_query(response.content), 'tree=%s' % tree.code)

        response = self.client.get(url, {'tree': [tree.code, 'xxx']})
        eq_(response.status_code, 404)

        tree2 = Tree.objects.create(
          code=tree.code + '2',
          l10n=tree.l10n
        )

        response = self.client.get(url, {'tree': [tree.code, tree2.code]})
        eq_(response.status_code, 200)
        eq_(get_query(response.content),
            'tree=%s&tree=%s' % (tree.code, tree2.code))

        response = self.client.get(url, {'av': appver.code})
        eq_(response.status_code, 200)
        eq_(get_query(response.content), 'av=%s' % appver.code)

        # combine them all
        data = {
          'locale': ['en-US', 'ta'],
          'av': [appver.code],
          'tree': [tree2.code, tree.code]
        }
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        query = get_query(response.content)
        for key, values in data.items():
            for value in values:
                ok_('%s=%s' % (key, value) in query)

    def test_dashboard_with_wrong_args(self):
        """dashboard() view takes arguments 'locale' and 'tree' and if these
        aren't correct that view should raise a 404"""
        url = reverse('shipping.views.dashboard')
        response = self.client.get(url, {'locale': 'xxx'})
        eq_(response.status_code, 404)

        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )

        locale, __ = Locale.objects.get_or_create(
          code='jp',
          name='Japanese',
        )

        response = self.client.get(url, {'locale': ['en-US', 'xxx']})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'locale': ['en-US', 'jp']})
        eq_(response.status_code, 200)

        # test the tree argument now
        response = self.client.get(url, {'tree': 'xxx'})
        eq_(response.status_code, 404)

        self._create_appver_milestone()
        assert Tree.objects.all().exists()
        tree, = Tree.objects.all()

        response = self.client.get(url, {'tree': ['xxx', tree.code]})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'tree': [tree.code]})
        eq_(response.status_code, 200)
