# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from elmo.test import TestCase
from django.contrib.auth.models import User, Permission
from django.test import override_settings


class SignOffTest(TestCase):
    # fixtures = ["test_repos.json", "test_pushes.json", "signoffs.json"]

    @override_settings(
        AUTHENTICATION_BACKENDS=('django.contrib.auth.backends.ModelBackend',),
    )
    def test_ensure_post(self):
        url = reverse('product-add-sign-off', args=('av', 'de', '4'))
        r = self.client.get(url)
        # require login, 302
        self.assertEqual(r.status_code, 302)
        user, _ = User.objects.get_or_create(username='l10ndriver')
        user.set_password('secret')
        user.save()
        user.user_permissions.set(
            Permission.objects.filter(
                codename__in=('add_signoff', 'review_signoff')
            )
        )
        assert self.client.login(username=user.username, password='secret')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 405)
