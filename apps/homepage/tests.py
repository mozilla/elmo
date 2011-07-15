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

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from nose.tools import eq_, ok_
from life.models import Locale
from commons.tests.mixins import EmbedsTestCaseMixin

class HomepageTestCase(TestCase, EmbedsTestCaseMixin):
    def setUp(self):
        super(HomepageTestCase, self).setUp()

        # SESSION_COOKIE_SECURE has to be True for tests to work.
        # The reason this might be switched off is if you have set it to False
        # in your settings/local.py so you can use http://localhost:8000/
        settings.SESSION_COOKIE_SECURE = True

        # side-step whatever authentication backend has been set up otherwise
        # we might end up trying to go online for some sort of LDAP lookup
        self._original_auth_backends = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (
          'django.contrib.auth.backends.ModelBackend',
        )

    def tearDown(self):
        super(HomepageTestCase, self).tearDown()
        settings.AUTHENTICATION_BACKENDS = self._original_auth_backends

    def test_secure_session_cookies(self):
        """secure session cookies should always be 'secure' and 'httponly'"""
        url = reverse('accounts.views.login')
        # run it as a mocked AJAX request because that's how elmo does it
        response = self.client.post(url,
          {'username':'peterbe', 'password':'secret'},
          **{'X-Requested-With':'XMLHttpRequest'})
        eq_(response.status_code, 200)
        ok_('class="errorlist"' in response.content)

        from django.contrib.auth.models import User
        user = User.objects.create(username='peterbe',
                                   first_name='Peter')
        user.set_password('secret')
        user.save()

        response = self.client.post(url,
          {'username':'peterbe',
           'password':'secret',
           'next': '/foo'},
          **{'X-Requested-With':'XMLHttpRequest'})
        # even though it's
        eq_(response.status_code, 302)
        ok_(response['Location'].endswith('/foo'))

        # if this fails it's because settings.SESSION_COOKIE_SECURE isn't true
        assert settings.SESSION_COOKIE_SECURE
        ok_(self.client.cookies['sessionid']['secure'])

        # if this fails it's because settings.SESSION_COOKIE_HTTPONLY isn't true
        assert settings.SESSION_COOKIE_HTTPONLY
        ok_(self.client.cookies['sessionid']['httponly'])

        # should now be logged in
        url = reverse('accounts.views.user_json')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # "Hi Peter" or something like that
        ok_('Peter' in response.content)

    def test_index_page(self):
        """load the current homepage index view"""
        url = reverse('homepage.views.index')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_teams_page(self):
        """check that the teams page renders correctly"""
        Locale.objects.create(
          code='en-US',
          name='English',
        )
        Locale.objects.create(
          code='sv-SE',
          name='Swedish',
        )

        url = reverse('homepage.views.teams')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_(-1 < response.content.find('English')
               < response.content.find('Swedish'))

    def test_team_page(self):
        """test a team (aka. locale) page"""
        Locale.objects.create(
          code='sv-SE',
          name='Swedish',
        )
        url = reverse('homepage.views.locale_team', args=['xxx'])
        response = self.client.get(url)
        # XXX would love for this to be a 404 instead (peterbe)
        eq_(response.status_code, 302)
        url = reverse('homepage.views.locale_team', args=['sv-SE'])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_('Swedish' in response.content)
