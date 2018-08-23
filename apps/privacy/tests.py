# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from elmo.test import TestCase
from django.utils.encoding import force_text
from django.contrib.auth.models import User, Permission
from django.contrib.admin.models import LogEntry, CHANGE
from .models import Policy, Comment
from elmo_commons.tests.mixins import EmbedsTestCaseMixin


class PrivacyTestCase(TestCase, EmbedsTestCaseMixin):

    def test_render_show_policy(self):
        url = reverse('privacy:show')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)
        content = force_text(response.content)
        self.assertIn('Policy not found', content)

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
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_render_policy_versions(self):
        url = reverse('privacy:versions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)

        add_url = reverse('privacy:add')
        data = {'content': "Bla bla", 'comment': "First"}
        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, 403)

        admin = User.objects.create_user(
          username='admin',
          email='admin@mozilla.com',
          password='secret',
        )
        assert self.client.login(username='admin', password='secret')
        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, 403)

        admin.user_permissions.add(
          Permission.objects.get(codename='add_policy')
        )
        admin.user_permissions.add(
          Permission.objects.get(codename='add_comment')
        )
        admin.save()
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response)

        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, 302, response.status_code)
        self.assertEqual(Policy.objects.all()[0].text, data['content'])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn(data['comment'], content)

        policy, = Policy.objects.all()
        self.assertFalse(policy.active)
        policy_url = reverse('privacy:show',
                             args=[policy.pk])
        content = force_text(response.content)
        self.assertIn(policy_url, content)

        # now activate it
        activate_url = reverse('privacy:activate')
        response = self.client.get(activate_url)
        # because you're not allowed yet
        self.assertEqual(response.status_code, 302)
        admin.user_permissions.add(
          Permission.objects.get(codename='activate_policy')
        )
        response = self.client.post(activate_url, {'active': 'xxx'})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(activate_url, {'active': policy.pk})
        self.assertEqual(response.status_code, 302)

        policy = Policy.objects.get(pk=policy.pk)
        self.assertTrue(policy.active)

        # starting to add another will suggest the current text
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(policy_url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn(data['content'], content)
        self.assert_all_embeds(response.content)

        # lastly post a comment to this policy
        data = {'policy': 'xxx', 'comment': 'Cool!'}
        comment_url = reverse('privacy:comment')
        response = self.client.post(comment_url, data)
        self.assertEqual(response.status_code, 404)
        data['policy'] = 123
        response = self.client.post(comment_url, data)
        self.assertEqual(response.status_code, 404)
        data['policy'] = policy.pk
        response = self.client.post(comment_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.get(text=data['comment']))
