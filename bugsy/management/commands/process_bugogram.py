from optparse import make_option
import os.path
from urllib2 import urlopen
import re

from django.core.management.base import BaseCommand, CommandError
try:
    import json
except ImportError:
    import simplejson as json

basebug = {
    "rep_platform":"All",
    "op_sys": "All",
    "product": "Mozilla Localizations",
    "component": "{{ component }}",
    "cc": "{{ bugmail }}"
}


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest = 'quiet', action = 'store_true',
                    help = 'Run quietly'),
        )
    help = 'TEMPORARY Download bugogram for new locales from wikimo'

    sectioner = re.compile('===? (.*?) ===?\n(.*?)(?===)', re.M|re.S)
    props = re.compile('^; (.*?) : (.*?)$', re.M|re.S)
    params = re.compile('%\((.*?)\)s')

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)

        page = urlopen('http://wiki.mozilla.org/index.php?title=L10n:Bugogram&action=raw').read()
        
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
        
        print json.dumps(allbugs, indent=2)
