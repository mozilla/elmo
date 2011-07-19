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

import posixpath
import urllib
import re
from nose.tools import eq_, ok_
from django.conf import settings
from django.contrib.staticfiles import finders

SCRIPTS_REGEX = re.compile('<script\s*[^>]*src=["\']([^"\']+)["\'].*?</script>',
                           re.M|re.DOTALL)
STYLES_REGEX = re.compile('<link.*?href=["\']([^"\']+)["\'].*?>',
                          re.M|re.DOTALL)

MISSING_STATIC_URL = re.compile('\!\{\s*STATIC_URL\s\}')

class EmbedsTestCaseMixin:
    """Checks that any static files referred to in the response exist.
    If running in debug mode we can rely on urlconf to serve it but because this
    is insecure it's not possible when NOT in debug mode.
    Running tests is always DEBUG=False so then we have to pretend we're
    django.contrib.staticfiles and do the look up manually.
    """

    def _check(self, response, regex, only_extension):
        for found in regex.findall(response):
            if found.endswith(only_extension):
                if settings.DEBUG:
                    resp = self.client.get(found)
                    eq_(resp.status_code, 200, found)
                else:
                    absolute_path = finders.find(
                      found.replace(settings.STATIC_URL, '')
                    )
                    ok_(absolute_path, found)

    def assert_all_embeds(self, response):
        if hasattr(response, 'content'):
            response = response.content
        response = re.sub('<!--(.*)-->', '', response, re.M)
        self._check(response, SCRIPTS_REGEX, '.js')
        self._check(response, STYLES_REGEX, '.css')

        # '{! STATIC_URL }' is something you might guess if the template does
        # a {{ STATIC_URL }} and the view doesn't use a RequestContext
        ok_(not MISSING_STATIC_URL.findall(response))
