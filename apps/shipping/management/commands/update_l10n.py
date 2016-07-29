# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Update all local clones to the revisions that are shipped with a milestone.
'''
from __future__ import absolute_import

import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from shipping.models import Milestone
from shipping.api import accepted_signoffs
from life.models import Push, Changeset
from django.conf import settings


class Command(BaseCommand):
    help = 'Update l10n repos to revisions shipped'

    def add_arguments(self, parser):
        parser.add_argument('milestone', help='milestone code')

    def handle(self, *args, **options):
        try:
            ms = Milestone.objects.get(code=options['milestone'])
        except:
            raise CommandError("No milestone with code %s found" %
                               options['milestone'])

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
