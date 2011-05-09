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

import re
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from nose.tools import eq_, ok_


class AccountsTestCase(TestCase):

    def test_login_long_username(self):
        url = reverse('django.contrib.auth.views.login')
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
        url = reverse('accounts.views.user_html')
        response = self.client.get(url)
        ok_(response.status_code, 200)
        ok_('Looong' in response.content)

    def test_login_form_allows_long_username(self):
        url = reverse('accounts.views.user_html')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        input_regex = re.compile('<input ([^>]+)>', re.M)
        for input_ in input_regex.findall(response.content):
            for name in re.findall('name="(.*?)"', input_):
                if name == 'username':
                    maxlength = re.findall('maxlength="(\d+)"', input_)[0]
                    ok_(maxlength.isdigit())
                    ok_(int(maxlength) > 30)
