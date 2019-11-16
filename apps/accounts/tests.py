# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import re
from elmo.test import TestCase
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.template import engines
from django.utils.encoding import force_text
from django.test import override_settings


@override_settings(
    AUTHENTICATION_BACKENDS=('django.contrib.auth.backends.ModelBackend',),
)
class AccountsTestCase(TestCase):

    def test_login_form_allows_long_username(self):
        url = reverse('login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        input_regex = re.compile('<input ([^>]+)>', re.M)
        for input_ in input_regex.findall(content):
            for name in re.findall('name="(.*?)"', input_):
                if name == 'username':
                    maxlength = re.findall(r'maxlength="(\d+)"', input_)[0]
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
            settings.MIDDLEWARE)
        self.assertNotIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE)

        self.assertIn('session_csrf', settings.INSTALLED_APPS)
