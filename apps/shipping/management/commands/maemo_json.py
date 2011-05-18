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

'''Export a json l10n-changesets including multi-locale information for
maemo builds.
'''

from optparse import make_option
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from shipping.models import Milestone, AppVersion
from shipping.views import _signoffs
from life.models import Changeset

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-a', '--app-version', dest = 'appver',
                    help = 'AppVersion to get signoffs for'),
        make_option('-m', '--milestone', dest = 'ms',
                    help = 'Milestone to get signoffs for'),
        )
    help = 'Create a l10n-changesets file for maemo'
    args = 'maemo-locales'

    def handle(self, *args, **options):
        appver = options.get('appver', None)
        if appver is None:
            ms = options.get('ms', None)
            if ms is not None:
                av_or_m = Milestone.objects.get(code=ms)
        else:
            av_or_m = AppVersion.objects.get(code=appver)
        if not args or av_or_m is None:
            return
        sos = _signoffs(av_or_m).annotate(tip=Max('push__changesets__id'))
        tips = dict(sos.values_list('locale__code', 'tip'))
        revmap = dict(Changeset.objects.filter(id__in=tips.values()).values_list('id', 'revision'))
        multi = map(lambda s: s.strip(), open(args[0]).readlines())
        chunks = []
        for loc in sorted(tips.keys()):
            platforms = ['"maemo"']
            if loc in multi:
                platforms.append('"maemo-multilocale"')
            platforms = ', '.join(platforms)
            chunks.append('''  "%(loc)s": {
    "revision": "%(rev)s",
    "platforms": [%(plat)s]
  }''' % {"loc":loc, "rev":revmap[tips[loc]][:12], "plat": platforms})
        out = "{\n%s\n}" % ",\n".join(chunks)
        print out
