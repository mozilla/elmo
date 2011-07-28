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
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
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

'''Temporary command to convert the bugogram on wikimo to a local json.
'''

from optparse import make_option
import os.path
from urllib2 import urlopen
import re

from django.core.management.base import BaseCommand
from django.utils import simplejson as json
import bugsy

basebug = {
  "rep_platform": "All",
  "op_sys": "All",
  "product": "Mozilla Localizations",
  "component": "{{ component }}",
  "cc": "{{ bugmail }}"
}

json_license = """{% comment %}
***** BEGIN LICENSE BLOCK *****
Version: MPL 1.1/GPL 2.0/LGPL 2.1

The contents of this file are subject to the Mozilla Public License Version
1.1 (the "License"); you may not use this file except in compliance with
the License. You may obtain a copy of the License at
http://www.mozilla.org/MPL/

Software distributed under the License is distributed on an "AS IS" basis,
WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
for the specific language governing rights and limitations under the
License.

The Original Code is l10n django site.

The Initial Developer of the Original Code is
Mozilla Foundation.
Portions created by the Initial Developer are Copyright (C) 2011
the Initial Developer. All Rights Reserved.

Contributor(s):

Alternatively, the contents of this file may be used under the terms of
either the GNU General Public License Version 2 or later (the "GPL"), or
the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
in which case the provisions of the GPL or the LGPL are applicable instead
of those above. If you wish to allow use of your version of this file only
under the terms of either the GPL or the LGPL, and not to allow others to
use your version of this file under the terms of the MPL, indicate your
decision by deleting the provisions above and replace them with the notice
and other provisions required by the GPL or the LGPL. If you do not delete
the provisions above, a recipient may use your version of this file under
the terms of any one of the MPL, the GPL or the LGPL.

***** END LICENSE BLOCK *****
{% endcomment %}
"""


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest='quiet', action='store_true',
                    help='Run quietly'),
        )
    help = 'TEMPORARY Download bugograms for new locales from wikimo'

    sectioner = re.compile('===? (.*?) ===?\n(.*?)(?===)', re.M | re.S)
    props = re.compile('^; (.*?) : (.*?)$', re.M | re.S)
    params = re.compile('%\((.*?)\)s')

    def handle(self, *args, **options):
        for alias, pn in (('fx', 'L10n:Bugogram'),
                          ('fennec', 'L10n:Mobile/Bugogram')):

            page = urlopen(
              'http://wiki.mozilla.org/index.php?title=%s&action=raw' % pn
              ).read()

            allbugs = []

            for section in self.sectioner.finditer(page):
                title = section.group(1)
                content = self.params.sub(lambda m: '{{ %s }}' % m.group(1),
                                      section.group(2))
                offset = 0
                props = {}
                for m in self.props.finditer(content):
                    offset = m.end(2)
                    props[m.group(1)] = m.group(2)
                if not props:
                    continue
                properties = basebug.copy()
                properties.update(props)
                properties['comment'] = content[offset:].strip()
                properties['title'] = title

                allbugs.append(properties)

            fname = os.path.join(*(bugsy.__path__ +
                                   ['templates',
                                    'bugsy',
                                    'new-%s-locales.json' % alias]))
            open(fname, 'w').write(
              json_license + json.dumps(allbugs, indent=2) + "\n")
