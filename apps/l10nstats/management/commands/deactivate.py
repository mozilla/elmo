# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import unicode_literals
from six.moves.configparser import ConfigParser
from six.moves import input
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urljoin

from django.core.management.base import BaseCommand

from l10nstats.models import Active


class Command(BaseCommand):

    def handle(self, **kwargs):
        self.handleApps(**kwargs)

    def handleApps(self, **kwargs):
        l10nbuilds = urlopen(
            'https://raw.githubusercontent.com/Pike/master-ball/'
            'master/l10n-master/l10nbuilds.ini')
        cp = ConfigParser()
        cp.readfp(l10nbuilds)
        for section in cp.sections():
            self.stdout.write(section + '\n')
            self.handleSection(section, dict(cp.items(section)))

    def handleSection(self, section, items):
        locales = items['locales']
        if locales == 'all':
            inipath = '/'.join((
                items['repo'], items['mozilla'],
                'raw-file', 'default',
                items['l10n.ini']
            ))
            ini = ConfigParser()
            ini.readfp(urlopen(inipath))
            allpath = urljoin(
                urljoin(inipath, ini.get('general', 'depth')),
                ini.get('general', 'all'))
            locales = urlopen(allpath).read()
        locales = locales.split()
        obs = (Active.objects
               .filter(run__tree__code=section)
               .exclude(run__locale__code__in=locales)
               .order_by('run__locale__code'))
        obslocs = ' '.join(obs.values_list('run__locale__code', flat=True))
        if not obslocs:
            self.stdout.write(' OK\n')
            return
        s = input('Remove %s? [Y/n] ' % obslocs)
        if s.lower() == 'y' or s == '':
            obs.delete()
