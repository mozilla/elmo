# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Checks the list of languages on https://localize.mozilla.org and compares
them against settings.VERBATIM_CONVERSIONS and suggests things that might
need to change.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from life.models import Locale


class Command(BaseCommand):  # pragma: no cover

    help = __doc__

    def handle(self, **options):
        # delay this import till run-time
        from BeautifulSoup import BeautifulSoup
        import urllib2

        soup = BeautifulSoup(urllib2.urlopen('https://localize.mozilla.org/').read())
        VERBATIM = {}
        for td in soup.findAll('td', attrs={'class':'language'}):
            a = td.find('a')
            lang = a.text
            code = a['href'].split('/')[1]
            assert lang and code
            VERBATIM[code] = lang

        ELMO = {}
        # exclude locales with teams
        aliased = (Locale.teams_over_time.related.model.objects
            .current()
            .values_list('locale', flat=True)
        )
        for l in Locale.objects.exclude(id__in=aliased):
            ELMO[l.code] = l.name

        linked_to = set()
        no_verbatim = set()
        orig_convert = settings.VERBATIM_CONVERSIONS
        proposed = {}
        for code in ELMO.iterkeys():
            gliblocale = code.replace('-', '_')
            # check for locales that are disabled, but exist
            if code in orig_convert:
                if orig_convert[code] is None and gliblocale in VERBATIM:
                    self.stdout.write("%s doesn't need mapping" % code)
                else:
                    proposed[code] = orig_convert[code]
                continue
            if gliblocale in VERBATIM:
                linked_to.add(gliblocale)
                continue
            self.stdout.write("%s not found on verbatim" % code)
            no_verbatim.add(code)
            proposed[code] = None

        if proposed == settings.VERBATIM_CONVERSIONS:
            return

        self.stdout.write("SUGGESTED NEW SETTING...\n")
        self.stdout.write("VERBATIM_CONVERSIONS = {")
        for key in sorted(proposed):
            key = str(key)
            value = proposed[key]
            if value:
                value = str(value)
            self.stdout.write(" " * 4 + "%r: %r," % (key, value))
        self.stdout.write("}")
        self.stdout.write("\n")
