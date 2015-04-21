# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""tests for templatetags in commons"""
from __future__ import absolute_import

from django.template import Template
from django.template import Context
from elmo.test import TestCase
from nose.tools import eq_, ok_

class TemplatetagsTestCase(TestCase):

    def test_bleach_safe(self):

        template_as_string = """
        {% load commons_filters %}
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
        context = Context({'msg':msg})
        rendered = template.render(context).strip()

        ok_('<a href="http://mozilla.org/page?a=b#top" rel="nofollow">http://m'\
            'ozilla.org/page?a=b#top</a>' in rendered)
        ok_('<a href="http://mozilla.com" rel="nofollow">mozilla.com</a>'
            in rendered)
        ok_('&lt;script&gt;alert(\'xss\')&lt;/script&gt;' in rendered)
        ok_('<strong>HTML</strong>' in rendered)
        ok_('&lt;textarea&gt;' in rendered)
