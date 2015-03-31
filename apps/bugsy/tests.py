# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from elmo.test import TestCase
from commons.tests.mixins import EmbedsTestCaseMixin
from life.models import Locale
from bugsy.views import homesnippet, teamsnippet


class BugsyTestCase(TestCase, EmbedsTestCaseMixin):

    def test_basic_render_index(self):
        url = reverse('bugsy.views.index')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_('There are currently ' in response.content)

    def test_basic_render_new_locale(self):
        url = reverse('bugsy.views.new_locale')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_basic_render_file_bugs(self):
        url = reverse('bugsy.views.file_bugs')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_new_locale_bugs_for_fx(self):
        url = reverse('bugsy.views.new_locale_bugs')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/javascript')
        struct = json.loads(response.content)
        ok_(struct)
        item = struct[0]
        ok_(item['product'])  # one of many

    def test_homesnippet(self):
        response = homesnippet()
        ok_(isinstance(response, basestring))
        index_url = reverse('bugsy.views.index')
        ok_('href="%s"' % index_url in response)

    def test_teamsnippet(self):
        de = Locale.objects.create(
          code='de',
        )
        response = teamsnippet(de)
        ok_(isinstance(response, basestring))
