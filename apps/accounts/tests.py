# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import re
from six.moves.urllib.parse import urlparse
from elmo.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.template import engines
from django.utils.encoding import force_text
from django.test import override_settings


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
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn('Please enter a correct', content)

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        url = reverse('user-json')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['user_name'], 'Looong')

    def test_login_form_allows_long_username(self):
        url = '/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        input_regex = re.compile('<input ([^>]+)>', re.M)
        for input_ in input_regex.findall(content):
            for name in re.findall('name="(.*?)"', input_):
                if name == 'username':
                    maxlength = re.findall('maxlength="(\d+)"', input_)[0]
                    self.assertTrue(maxlength.isdigit())
                    self.assertTrue(int(maxlength) > 30)

    def test_user_json(self):
        url = reverse('user-json')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['csrf_token'])
        self.assertNotEqual(data['csrf_token'], 'NOTPROVIDED')

        token_key = response.cookies['anoncsrf'].value
        # before we can pick up from the cache we need to know
        # what prefix it was stored with
        from session_csrf import prep_key
        # session_csrf hashes the combined key to normalize its potential
        # max length
        cache_key = prep_key(token_key)
        self.assertEqual(cache.get(cache_key), data['csrf_token'])
        self.assertNotIn('user_name', data)

        user = User.objects.create_user(
          'something_short',
          'an.email.that.is@very.looong.com',
          'secret'
        )
        user.save()
        assert self.client.login(username=user.username,
                                 password='secret')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['user_name'], user.username)
        self.assertNotIn('csrf_token', data)

        user.first_name = "Peter"
        user.last_name = "Bengtsson"
        user.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['user_name'], "Peter")

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
        self.assertEqual(response.status_code, 302)
        path = urlparse(response['Location']).path
        self.assertEqual(path, '/')

        response = self.client.get(reverse('user-json'))
        data = json.loads(response.content)
        self.assertNotIn('user_name', data)

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
        response = self.client.get(url, {REDIRECT_FIELD_NAME: '/foo/bar'})
        self.assertEqual(response.status_code, 302)
        path = urlparse(response['Location']).path
        self.assertEqual(path, '/foo/bar')

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
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn('error', content)
        self.assertIn('value="%s"' % user.username, content)
        self.assertIn('text/html', response['Content-Type'])

        # if the password is wrong it doesn't matter if it's an AJAX request
        response = self.client.post(url, {'username': user.username,
                                          'password': 'wrong'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn('error', content)
        self.assertIn('value="%s"' % user.username, content)

        # but get it right and as AJAX and you get JSON back
        response = self.client.post(url, {'username': user.username,
                                          'password': 'secret'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['user_name'], user.username)
        self.assertIn('application/json', response['Content-Type'])
        self.assertIn('private', response['Cache-Control'])

        user.first_name = "Peter"
        user.last_name = "Bengtsson"
        user.save()
        response = self.client.post(url, {'username': user.username,
                                          'password': 'secret'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['user_name'], "Peter")

    def test_django_session_csrf(self):
        """test that we're correctly using session CSRF tokens
        (as opposed to cookies) for all template engines"""
        import session_csrf
        import django.template.context_processors
        for engine in engines.all():
            # ensure that session_csrf comes after django.template...
            processors = engine.engine.template_context_processors
            self.assertEqual(
                processors.count(django.template.context_processors.csrf),
                1)
            self.assertEqual(
                processors.count(session_csrf.context_processor),
                1)
            self.assertLess(
                processors.index(django.template.context_processors.csrf),
                processors.index(session_csrf.context_processor),
                msg='sessions_csrf needs to be after django default')

        self.assertIn(
            'session_csrf.CsrfMiddleware',
            settings.MIDDLEWARE_CLASSES)
        self.assertNotIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE_CLASSES)

        self.assertIn('session_csrf', settings.INSTALLED_APPS)

        login_url = reverse('user-json')

        assert not self.client.cookies
        response = self.client.get(login_url)
        self.assertTrue(self.client.cookies['anoncsrf'])

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
        content = force_text(response.content)
        self.assertIn('href="/#login"', content)
        assert self.client.login(username='admin', password='secret')
        response = self.client.get(url)
        content = force_text(response.content)
        self.assertTrue(
            re.findall('name=[\'"]csrfmiddlewaretoken[\'"]', content))
