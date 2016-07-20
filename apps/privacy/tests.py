# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from nose.tools import eq_, ok_
from django.core.urlresolvers import reverse
from elmo.test import TestCase
from django.contrib.auth.models import User, Permission
from django.contrib.admin.models import LogEntry, CHANGE
from django.conf import settings
from .models import Policy, Comment
from commons.tests.mixins import EmbedsTestCaseMixin


class PrivacyTestCase(TestCase, EmbedsTestCaseMixin):

    def test_render_show_policy(self):
        url = reverse('privacy.views.show_policy')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_('Policy not found' in response.content)

        user = User.objects.create(
          username='peter'
        )
        policy = Policy.objects.create(
          text="Hi Mozilla",
          active=True
        )
        LogEntry.objects.create(
          content_type=Policy.contenttype(),
          user=user,
          object_id=policy.id,
          action_flag=CHANGE,
          change_message='activate'
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_render_policy_versions(self):
        url = reverse('privacy.views.versions')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

        add_url = reverse('privacy.views.add_policy')
        data = {'content': "Bla bla", 'comment': "First"}
        response = self.client.post(add_url, data)
        eq_(response.status_code, 403)

        admin = User.objects.create_user(
          username='admin',
          email='admin@mozilla.com',
          password='secret',
        )
        assert self.client.login(username='admin', password='secret')
        response = self.client.post(add_url, data)
        eq_(response.status_code, 403)

        admin.user_permissions.add(
          Permission.objects.get(codename='add_policy')
        )
        admin.user_permissions.add(
          Permission.objects.get(codename='add_comment')
        )
        admin.save()
        response = self.client.get(add_url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response)

        response = self.client.post(add_url, data)
        eq_(response.status_code, 302, response.status_code)
        eq_(Policy.objects.all()[0].text, data['content'])

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(data['comment'] in response.content)

        policy, = Policy.objects.all()
        ok_(not policy.active)
        policy_url = reverse('privacy.views.show_policy',
                             args=[policy.pk])
        ok_(policy_url in response.content)

        # now activate it
        activate_url = reverse('privacy.views.activate_policy')
        response = self.client.get(activate_url)
        # because you're not allowed yet
        eq_(response.status_code, 302)
        admin.user_permissions.add(
          Permission.objects.get(codename='activate_policy')
        )
        response = self.client.post(activate_url, {'active': 'xxx'})
        eq_(response.status_code, 404)
        response = self.client.post(activate_url, {'active': policy.pk})
        eq_(response.status_code, 302)

        policy = Policy.objects.get(pk=policy.pk)
        ok_(policy.active)

        # starting to add another will suggest the current text
        response = self.client.get(add_url)
        eq_(response.status_code, 200)

        response = self.client.get(policy_url)
        eq_(response.status_code, 200)
        ok_(data['content'] in response.content)
        self.assert_all_embeds(response.content)

        # lastly post a comment to this policy
        data = {'policy': 'xxx', 'comment': 'Cool!'}
        comment_url = reverse('privacy.views.add_comment')
        response = self.client.post(comment_url, data)
        eq_(response.status_code, 404)
        data['policy'] = 123
        response = self.client.post(comment_url, data)
        eq_(response.status_code, 404)
        data['policy'] = policy.pk
        response = self.client.post(comment_url, data)
        eq_(response.status_code, 302)
        ok_(Comment.objects.get(text=data['comment']))
