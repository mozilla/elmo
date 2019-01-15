# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from elmo.test import TestCase
from six.moves.urllib.parse import urlparse
from django.http import QueryDict
from django.core.urlresolvers import reverse
import l10nstats.views
import shipping.views


class L10nstatsTestCase(TestCase):

    def test_render_index_legacy(self):
        """the old dashboard should redirect to the shipping dashboard"""
        url = reverse(l10nstats.views.index)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 301)
        self.assertIn(
            reverse(shipping.views.index),
            urlparse(response['location']).path)

        # now try it with a query string as well
        response = self.client.get(url, {'av': 'fx 1.0'})
        self.assertEqual(response.status_code, 301)

        qd = QueryDict(urlparse(response['location']).query)
        self.assertEqual(qd['av'], 'fx 1.0')
        self.assertIn(
            reverse(shipping.views.index),
            urlparse(response['location']).path)
