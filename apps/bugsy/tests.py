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

from nose.tools import eq_, ok_
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from test_utils import TestCase
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
