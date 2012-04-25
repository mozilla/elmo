# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from urlparse import urlparse
from nose.tools import eq_, ok_
from django.http import QueryDict
from django.core.urlresolvers import reverse
from apps.shipping.tests.test_views import ShippingTestCaseBase
from apps.life.models import Tree, Locale
from apps.mbdb.models import Build
from models import Run, Active
from commons.tests.mixins import EmbedsTestCaseMixin


class L10nstatsTestCase(ShippingTestCaseBase, EmbedsTestCaseMixin):
    fixtures = ['one_started_l10n_build.json']

    def _create_active_run(self):
        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        tree = Tree.objects.all()[0]
        build = Build.objects.all()[0]
        run = Run.objects.create(
          locale=locale,
          tree=tree,
          build=build,
          srctime=datetime.datetime.now(),
        )
        Active.objects.create(run=run)
        return run

    def test_history_static_files(self):
        """render the tree_status view and check that all static files are
        accessible"""
        appver, milestone = self._create_appver_milestone()
        url = reverse('l10nstats.views.history_plot')
        response = self.client.get(url)
        eq_(response.status_code, 404)
        tree, = Tree.objects.all()
        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        data = {'tree': tree.code, 'locale': locale.code}
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_tree_status_static_files(self):
        """render the tree_status view and check that all static files are
        accessible"""
        appver, milestone = self._create_appver_milestone()

        url = reverse('l10nstats.views.tree_progress', args=['XXX'])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        # _create_appver_milestone() creates a mock tree
        tree, = Tree.objects.all()
        url = reverse('l10nstats.views.tree_progress', args=[tree.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('no statistics for %s' % tree.code in response.content)

        self._create_active_run()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        self.assert_all_embeds(response.content)

    def test_render_index_legacy(self):
        """the old dashboard should redirect to the shipping dashboard"""
        url = reverse('l10nstats.views.index')
        response = self.client.get(url)

        eq_(response.status_code, 301)
        ok_(reverse('shipping.views.index') in
             urlparse(response['location']).path)

        # now try it with a query string as well
        response = self.client.get(url, {'av': 'fx 1.0'})
        eq_(response.status_code, 301)

        qd = QueryDict(urlparse(response['location']).query)
        eq_(qd['av'], 'fx 1.0')
        ok_(reverse('shipping.views.index') in
             urlparse(response['location']).path)

    def test_compare_with_invalid_id(self):
        """trying to run a compare with an invalid Run ID shouldn't cause a 500
        error. Instead it should return a 400 error.

        See https://bugzilla.mozilla.org/show_bug.cgi?id=698634
        """

        url = reverse('l10nstats.views.compare')
        response = self.client.get(url, {'run': 'xxx'})
        eq_(response.status_code, 400)

        # and sane but unknown should be 404
        response = self.client.get(url, {'run': 123})
        eq_(response.status_code, 404)
