# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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
        make_option('-q', '--quiet', dest='quiet', action='store_true',
                    help='Run quietly'),
        )
    help = 'Update l10n repos to revisions shipped'
    args = 'milestone code'

    def handle(self, *args, **options):
        # quiet = options.get('quiet', False)  # not used
        if not args:
            return
        try:
            ms = Milestone.objects.get(code=args[0])
        except:
            raise CommandError("No milestone with code %s found" % args[0])

        forest = ms.appver.trees_over_time.latest().tree.l10n.name.split('/')

        def resolve(path):
            return os.path.join(settings.REPOSITORY_BASE,
                                *(forest + path.split('/')))

        if ms.status == Milestone.SHIPPED:
            sos = ms.signoffs
        else:
            sos = accepted_signoffs(ms.appver)
        sos = dict(sos.values_list('locale__code', 'push_id'))
        tips = dict(Push.objects
                    .filter(id__in=sos.values())
                    .annotate(tip=Max('changesets__id'))
                    .values_list('id', 'tip'))
        revs = dict(Changeset.objects
                    .filter(id__in=tips.values())
                    .values_list('id', 'revision'))
        from mercurial import dispatch
        for loc in sorted(sos.keys()):
            repopath = resolve(loc)
            rev = revs[tips[sos[loc]]]
            dispatch.dispatch(
                dispatch.request(['update', '-R', repopath, '-r', rev])
                )
