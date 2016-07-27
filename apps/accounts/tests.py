# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import re
from urlparse import urlparse
from elmo.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
import json
from django.core.cache import cache
from django.test import override_settings
from nose.tools import eq_, ok_


@override_settings(
    AUTHENTICATION_BACKENDS=('lib.auth.backends.MozLdapBackend',),
    LDAP_HOST=None,
    LDAP_DN=None,
    LDAP_PASSWORD=None,
)
class AccountsTestCase(TestCase):

    def test_login_long_username(self):
        url = reverse('login')
        data = dict(
          username='some_with_a_really_long@emailaddress.com',
          password='secret'
        )
        user = User(**dict(username='something_short',
                           email=data['username'],
                           first_name="Looong"))
        user.set_password(data['password'])
        user.save()

        # first get the password wrong
        response = self.client.post(url, dict(data, password='WRONG!'))
        ok_(response.status_code, 200)
        ok_('Please enter a correct' in response.content)

        response = self.client.post(url, data)
        ok_(response.status_code, 302)
        url = reverse('user-json')
        response = self.client.get(url)
        ok_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        eq_(data['user_name'], 'Looong')

    def test_login_form_allows_long_username(self):
        url = '/'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        input_regex = re.compile('<input ([^>]+)>', re.M)
        for input_ in input_regex.findall(response.content):
            for name in re.findall('name="(.*?)"', input_):
                if name == 'username':
                    maxlength = re.findall('maxlength="(\d+)"', input_)[0]
                    ok_(maxlength.isdigit())
                    ok_(int(maxlength) > 30)

    def test_user_json(self):
        url = reverse('user-json')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(data['csrf_token'])
        ok_(data['csrf_token'] != 'NOTPROVIDED')

        token_key = response.cookies['anoncsrf'].value
        # before we can pick up from the cache we need to know
        # what prefix it was stored with
        from session_csrf import prep_key
        # session_csrf hashes the combined key to normalize its potential
        # max length
        cache_key = prep_key(token_key)
        eq_(cache.get(cache_key), data['csrf_token'])
        ok_('user_name' not in data)

        user = User.objects.create_user(
          'something_short',
          'an.email.that.is@very.looong.com',
          'secret'
        )
        user.save()
        assert self.client.login(username=user.username,
                                 password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['user_name'], user.username)
        ok_('csrf_token' not in data)

        user.first_name = "Peter"
        user.last_name = "Bengtsson"
        user.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['user_name'], "Peter")

    def test_logout(self):
        url = reverse('logout')
        user = User.objects.create_user(
          'something_short',
          'an.email.that.is@very.looong.com',
          'secret'
        )
        user.save()
        assert self.client.login(username=user.username,
                                 password='secret')

        response = self.client.get(url)  # note: it's GET
        eq_(response.status_code, 302)
        path = urlparse(response['Location']).path
        eq_(path, '/')

        response = self.client.get(reverse('user-json'))
        data = json.loads(response.content)
        ok_('user_name' not in data)

    def test_logout_with_next_url(self):
        url = reverse('logout')
        user = User.objects.create_user(
          'something_short',
          'an.email.that.is@very.looong.com',
          'secret'
        )
        user.save()
        assert self.client.login(username=user.username,
                                 password='secret')
        from django.contrib.auth.views import REDIRECT_FIELD_NAME
        response = self.client.get(url,
          {REDIRECT_FIELD_NAME: '/foo/bar'}
        )
        eq_(response.status_code, 302)
        path = urlparse(response['Location']).path
        eq_(path, '/foo/bar')

    def test_ajax_login(self):
        url = reverse('login')

        user = User.objects.create_user(
          'something_short',
          'an.email.that.is@very.looong.com',
          'secret'
        )
        user.save()
        response = self.client.post(url, {'username': user.username,
                                          'password': 'wrong'})
        eq_(response.status_code, 200)
        ok_('error' in response.content)
        ok_('value="%s"' % user.username in response.content)
        ok_('text/html' in response['Content-Type'])

        # if the password is wrong it doesn't matter if it's an AJAX request
        response = self.client.post(url, {'username': user.username,
                                          'password': 'wrong'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        eq_(response.status_code, 200)
        ok_('error' in response.content)
        ok_('value="%s"' % user.username in response.content)

        # but get it right and as AJAX and you get JSON back
        response = self.client.post(url, {'username': user.username,
                                          'password': 'secret'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['user_name'], user.username)
        ok_('application/json' in response['Content-Type'])
        ok_('private' in response['Cache-Control'])

        user.first_name = "Peter"
        user.last_name = "Bengtsson"
        user.save()
        response = self.client.post(url, {'username': user.username,
                                          'password': 'secret'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['user_name'], "Peter")

    def test_django_session_csrf(self):
        """test that we're correctly using session CSRF tokens
        (as opposed to cookies)"""
        ok_('session_csrf.context_processor'
            in settings.TEMPLATE_CONTEXT_PROCESSORS)
        ok_('django.core.context_processors.csrf'
            not in settings.TEMPLATE_CONTEXT_PROCESSORS)

        ok_('session_csrf.CsrfMiddleware' in settings.MIDDLEWARE_CLASSES)
        ok_('django.middleware.csrf.CsrfViewMiddleware'
            not in settings.MIDDLEWARE_CLASSES)

        ok_('session_csrf' in settings.INSTALLED_APPS)
        # funfactory initiates an important monkeypatch which we need
        ok_('funfactory' in settings.INSTALLED_APPS)

        login_url = reverse('user-json')

        cookies_before = self.client.cookies
        assert not self.client.cookies
        response = self.client.get(login_url)
        ok_(self.client.cookies['anoncsrf'])

        admin = User.objects.create(
          username='admin',
          is_staff=True,
          is_superuser=True,
        )
        admin.set_password('secret')
        admin.save()

        # any page with a POST form will do
        url = reverse('privacy:add')
        response = self.client.get(url)
        ok_('href="/#login"' in response.content)
        assert self.client.login(username='admin', password='secret')
        response = self.client.get(url)
        ok_(re.findall('name=[\'"]csrfmiddlewaretoken[\'"]', response.content))
