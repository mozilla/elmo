# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from shipping.tests.test_views import ShippingTestCaseBase
from life.models import Tree, Locale
from ..models import Run, Active


class L10nstatsTestCase(ShippingTestCaseBase):

    def _create_active_run(self):
        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        tree = Tree.objects.all()[0]
        run = Run.objects.create(
          locale=locale,
          tree=tree,
          build=None,
          srctime=datetime.datetime.utcnow(),
        )
        Active.objects.create(run=run)
        return run

    def test_history_static_files(self):
        """render the tree_status view and check that all static files are
        accessible"""
        appver, tree = self._create_appver_tree()
        url = reverse('locale-tree-history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        data = {'tree': tree.code, 'locale': locale.code}
        # good locale, good tree, but not building
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 404)
        # good locale, good tree, and building, 200
        self._create_active_run()
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_tree_status_static_files(self):
        """render the tree_status view and check that all static files are
        accessible"""
        appver, tree = self._create_appver_tree()

        url = reverse('tree-history', args=['XXX'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # _create_appver_tree() creates a mock tree
        url = reverse('tree-history', args=[tree.code])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn('no statistics for %s' % tree.code, content)

        self._create_active_run()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assert_all_embeds(response.content)
