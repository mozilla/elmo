# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""tests for bleach filter"""
from __future__ import absolute_import

from django.template import Template
from django.template import Context
from elmo.test import TestCase


class BleachFilterTestCase(TestCase):

    def test_bleach_safe(self):

        template_as_string = """
        {% load bleach_filters %}
        {{ msg|bleach_safe }}
        """
        template = Template(template_as_string)
        msg = u"""
        A url first: http://mozilla.org/page?a=b#top
        or a link <a href="http://mozilla.com">mozilla.com</a>
        nasty stuff: <script>alert('xss')</script>
        basic <strong>HTML</strong>
        but not so basic: <textarea>
        """.strip()
        context = Context({'msg': msg})
        rendered = template.render(context).strip()

        self.assertIn(
            '<a href="http://mozilla.org/page?a=b#top" rel="nofollow">'
            'http://mozilla.org/page?a=b#top</a>',
            rendered)
        self.assertIn(
            '<a href="http://mozilla.com" rel="nofollow">mozilla.com</a>',
            rendered)
        self.assertIn('&lt;script&gt;alert(\'xss\')&lt;/script&gt;', rendered)
        self.assertIn('<strong>HTML</strong>', rendered)
        self.assertIn('&lt;textarea&gt;', rendered)
