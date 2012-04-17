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

'''Update all local clones to the revisions that are shipped with a milestone.
'''

from optparse import make_option
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from shipping.models import Milestone
from shipping.api import accepted_signoffs
from life.models import Push, Changeset
from django.conf import settings

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest = 'quiet', action = 'store_true',
                    help = 'Run quietly'),
        )
    help = 'Update l10n repos to revisions shipped'
    args = 'milestone code'

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        if not args:
            return
        try:
            ms = Milestone.objects.get(code=args[0])
        except:
            raise CommandError, "No milestone with code %s found" % args[0]

        forest = ms.appver.tree.l10n.name.split('/')
        def resolve(path):
            return os.path.join(settings.REPOSITORY_BASE, *(forest + path.split('/')))

        if ms.status == Milestone.SHIPPED:
            sos = ms.signoffs
        else:
            sos = accepted_signoffs(id=ms.appver_id)
        sos=dict(sos.values_list('locale__code', 'push_id'))
        tips = dict(Push.objects.filter(id__in=sos.values()).annotate(tip=Max('changesets__id')).values_list('id', 'tip'))
        revs = dict(Changeset.objects.filter(id__in=tips.values()).values_list('id','revision'))
        from mercurial import dispatch
        for loc in sorted(sos.keys()):
            repopath = resolve(loc)
            rev = revs[tips[sos[loc]]]
            dispatch.dispatch(
                dispatch.request(['update', '-R', repopath, '-r', rev])
                )
