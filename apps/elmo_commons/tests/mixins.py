# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import re
from django.conf import settings
from django.contrib.staticfiles import finders
from django.urls import resolve
from django.utils.encoding import force_text
from six.moves.urllib.parse import urlparse

SCRIPTS_REGEX = re.compile(
    '<script\s*[^>]*src=["\']([^"\']+)["\'].*?</script>',
    re.M | re.DOTALL)
STYLES_REGEX = re.compile('<link.*?href=["\']([^"\']+)["\'].*?>',
                          re.M | re.DOTALL)
WHITELIST = {
}


class EmbedsTestCaseMixin:
    """Checks that any static files referred to in the response exist.
    If running in debug mode we can rely on urlconf to serve it but because
    this is insecure it's not possible when NOT in debug mode.
    Running tests is always DEBUG=False so then we have to pretend we're
    django.contrib.staticfiles and do the look up manually.
    """

    def _check(self, response, regex):
        for found in regex.findall(response):
            if found.startswith('//'):
                # external urls like tabzilla, ignore
                continue
            url = urlparse(found)
            if url.netloc:
                # external url, too.
                continue
            path = url.path
            if path in WHITELIST:
                continue
            if path.startswith(settings.STATIC_URL):
                absolute_path = finders.find(
                    path[len(settings.STATIC_URL):]
                )
                self.assertTrue(absolute_path, found + " not found")
            else:
                resolve(path)

    def assert_all_embeds(self, response):
        if hasattr(response, 'content'):
            response = response.content
        response = force_text(response)
        response = re.sub('<!--(.*)-->', '', response, re.M)
        self._check(response, SCRIPTS_REGEX)
        self._check(response, STYLES_REGEX)
