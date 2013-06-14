# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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
            if found.startswith('//'):
                # external urls like tabzilla, ignore
                continue
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
