# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import re
from elmo.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
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

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        url = reverse('user-json')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['user_name'], 'Looong')

    def test_login_form_allows_long_username(self):
        url = reverse('login')
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

        user.first_name = "Peter"
        user.last_name = "Bengtsson"
        user.save()

        response = self.client.get(url)
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
