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
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Peter Bengtsson <peterbe@mozilla.com>
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

import datetime
from urlparse import urlparse
from nose.tools import eq_, ok_
from django.http import QueryDict
from django.core.urlresolvers import reverse
from apps.shipping.tests import ShippingTestCaseBase
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
