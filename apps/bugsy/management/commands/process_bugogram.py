# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Temporary command to convert the bugogram on wikimo to a local json.
'''

from optparse import make_option
import os.path
from urllib2 import urlopen
import re

from django.core.management.base import BaseCommand
import json
import bugsy

basebug = {
  "rep_platform": "All",
  "op_sys": "All",
  "product": "Mozilla Localizations",
  "component": "{{ component }}",
  "cc": "{{ bugmail }}"
}

json_license = """{% comment %}
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
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
