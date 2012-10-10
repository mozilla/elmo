# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Checks the list of languages on https://localize.mozilla.org and compares
them against settings.VERBATIM_CONVERSIONS and suggests things that might
need to change.

Requires `pyquery` to be installed. See requirements/dev.txt
"""

import re
from django.conf import settings
from django.core.management.base import BaseCommand
from life.models import Locale


class Command(BaseCommand):  # pragma: no cover

    help = __doc__

    def handle(self, **options):
        # delay this import till run-time
        from pyquery import PyQuery as pq

        d = pq(url='https://localize.mozilla.org/')
        VERBATIM = {}
        for each in d('td.language a'):
            lang = each.text
            code = each.attrib['href'].split('/')[1]
            assert lang and code
            VERBATIM[code] = lang

        ELMO = {}
        for l in Locale.objects.all():
            ELMO[l.code] = l.name

        ending = re.compile('-[A-Z]{2}')

        not_matched = set()
        conversions = {}
        for code, name in ELMO.items():
            if code in VERBATIM:
                pass
            elif code.replace('-', '_') in VERBATIM:
                pass
            elif ending.findall(code) and code.split('-')[0] in VERBATIM:
                conversions[code] = code.split('-')[0]
                continue
            else:
                not_matched.add(code)

        combined = {}
        for code in not_matched:
            combined[code] = None
        for key, value in conversions.items():
            combined[key] = value

        if combined == settings.VERBATIM_CONVERSIONS:
            return

        print "SUGGESTED NEW SETTING..."
        print
        print "VERBATIM_CONVERSIONS = {"
        for key in sorted(combined):
            key = str(key)
            value = combined[key]
            if value:
                value = str(value)
            print " " * 4 + "%r: %r," % (key, value)
        print "}"
        print "\n"

        print "POTENTIAL PROBLEMS..."
        print
        for each in combined:
            if each not in settings.VERBATIM_CONVERSIONS:
                print "\tMissing".ljust(20), each
            elif combined[each] != settings.VERBATIM_CONVERSIONS[each]:
                print "\tMismatch".ljust(20), each.ljust(10),
                print repr(settings.VERBATIM_CONVERSIONS[each]), '-->',
                print repr(combined[each])
        for each in settings.VERBATIM_CONVERSIONS:
            if each not in combined:
                print "\tExcessive".ljust(20), each
