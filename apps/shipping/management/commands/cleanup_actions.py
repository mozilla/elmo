# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Update all local clones to the revisions that are shipped with a milestone.
'''

from collections import defaultdict
from optparse import make_option

from django.core.management.base import BaseCommand
from shipping.models import Action


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest='quiet', action='store_true',
                    help='Run quietly'),
        make_option('-n', '--dry-run', dest='dry', action='store_true',
                    help='Do not actually remove actions'),
        )
    help = 'Clean up actions that have been excessively cloned'

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        dry = options.get('dry', False)
        aq = Action.objects.order_by('-when')
        if not quiet:
            print 'Total action count at start: ', aq.count()
        cut = aq.values_list('when', flat=True)[0]
        while cut is not None:
            try:
                next_cut = (aq.filter(when__lt=cut)
                            .values_list('when', flat=True)[100])
            except IndexError:
                next_cut = None
            slice = aq.filter(when__lte=cut)
            if next_cut is not None:
                slice = slice.filter(when__gte=next_cut)
            c = defaultdict(list)
            for a in slice:
                c[(a.when, a.author_id, a.signoff_id, a.flag)].append(a.id)
            dupes = dict(filter(lambda t: len(t[1]) > 1, c.iteritems()))
            obsolete = []
            for a_ids in dupes.itervalues():
                obsolete += a_ids[:-1]
            if not quiet and obsolete:
                print 'Deleting %d actions' % len(obsolete)
            if not dry and obsolete:
                Action.objects.filter(id__in=obsolete).delete()
            cut = next_cut
        if not quiet:
            print 'Total action count now: ', aq.count()
