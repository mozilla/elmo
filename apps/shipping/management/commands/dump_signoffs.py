# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Update all local clones to the revisions that are shipped with a milestone.
'''

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Max
from life.models import Push, Changeset
from shipping.api import accepted_signoffs
import json


class Command(BaseCommand):
    help = 'Dump all latest accepted signoffs for appversions as JSON'

    def handle(self, *args, **options):
        sos = accepted_signoffs()
        triples = list(sos
                       .order_by('appversion__code', 'locale__code')
                       .values_list('appversion__code',
                                    'locale__code',
                                    'push'))
        pushes = set(t[2] for t in triples)
        cs4push = dict(Push.objects
                       .filter(id__in=pushes)
                       .annotate(tip=Max("changesets"))
                       .values_list('id', 'tip'))
        revs = dict(Changeset.objects
                    .filter(id__in=cs4push.values())
                    .values_list('id', 'revision'))

        rv = defaultdict(dict)
        for av, loc, pushid in triples:
            rv[av][loc] = revs[cs4push[pushid]][:12]

        print json.dumps(rv, indent=2, sort_keys=True)
