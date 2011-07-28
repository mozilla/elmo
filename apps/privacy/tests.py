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
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.contrib.admin.models import LogEntry, CHANGE
from models import Policy, Comment
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
