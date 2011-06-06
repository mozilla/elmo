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
#    Peter Bengtsson <peterbe@mozilla.com>
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

"""tests for templatetags in commons"""

from django.template import Template
from django.template import Context
from django.test import TestCase
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
