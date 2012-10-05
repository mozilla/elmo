# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_
from test_utils import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from shipping.models import Milestone, Application, AppVersion


class ShippingReleaseTestCase(TestCase):

    def test_create_milestones(self):
        url = reverse('shipping.views.release.create_milestones')
        eq_(self.client.get(url).status_code, 405)

        # not logged in
        eq_(self.client.post(url).status_code, 302)

        admin = User.objects.create_user(
            'admin',
            'admin@example.com',
            'secret'
        )
        admin.is_superuser = True
        admin.save()
        self.client.login(username='admin', password='secret')

        # Send the special POST variables
        new_milestones = {
            'av': 'fx13',
            'code-fx13': 'fx_beta_b6',
            'name-fx13': 'Beta Build 6'
        }
        response = self.client.post(url, new_milestones)
        # expect it to 404 because this is not a recognized appversion
        eq_(response.status_code, 404)

        # To avoid the 404, make sure we have the AppVersion
        app = Application.objects.create(
            name='Firefox',
            code='fx',
        )
        appver = AppVersion.objects.create(
            app=app,
            version='13',
            code='fx13',
        )

        # before we do it properly, try by messing up the input
        no_code_data = {
            'av': 'fx13',
            'xxx': 'yyy',
            'name-fx13': 'Beta Build 6'
        }
        response = self.client.post(url, no_code_data)
        # should fail because there's no "code"
        eq_(response.status_code, 400)

        # proper input and matching AppVersion
        response = self.client.post(url, new_milestones)
        # redirecting means it worked
        eq_(response.status_code, 302)

        # double-checking against the database
        ok_(Milestone.objects.all().exists())
        ok_(Milestone.objects.filter(code='fx_beta_b6').exists())
        ok_(Milestone.objects.filter(appver__code=appver.code).exists())

        # don't try to do it again
        response = self.client.post(url, new_milestones)
        eq_(response.status_code, 400)

    def test_create_milestone_with_blank_name(self):
        """proves that we solved
        https://bugzilla.mozilla.org/show_bug.cgi?id=798529
        """
        url = reverse('shipping.views.release.create_milestones')

        admin = User.objects.create_user(
            'admin',
            'admin@example.com',
            'secret'
        )
        admin.is_superuser = True
        admin.save()
        self.client.login(username='admin', password='secret')

        app = Application.objects.create(
            name='Firefox',
            code='fx',
        )
        AppVersion.objects.create(
            app=app,
            version='13',
            code='fx13',
        )

        # Send the special POST variables
        new_milestones = {
            'av': 'fx13',
            'code-fx13': 'fx_beta_b6',
            'name-fx13': ''
        }
        response = self.client.post(url, new_milestones)
        # redirecting means it worked
        eq_(response.status_code, 302)

        ok_(Milestone.objects.filter(name=''))
