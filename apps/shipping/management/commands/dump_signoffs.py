# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Update all local clones to the revisions that are shipped with a milestone.
'''

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Max
from life.models import Push, Changeset
from shipping.models import Action
from shipping.api import flags4appversions
import json


class Command(BaseCommand):
    help = 'Dump all latest accepted signoffs for appversions as JSON'

    def handle(self, *args, **options):
        locflags4av = flags4appversions()
        actions = set()
        for flags4loc in locflags4av.itervalues():
            for real_av, flags in flags4loc.itervalues():
                if Action.ACCEPTED in flags:
                    actions.add(flags[Action.ACCEPTED])
        push4action = dict(Action.objects
                           .filter(id__in=actions)
                           .values_list('id', 'signoff__push'))
        cs4push = dict(Push.objects
                       .filter(id__in=set(push4action.values()))
                       .annotate(tip=Max("changesets"))
                       .values_list('id', 'tip'))
        revs = dict(Changeset.objects
                    .filter(id__in=cs4push.values())
                    .values_list('id', 'revision'))

        rv = defaultdict(dict)
        for av, flags4loc in locflags4av.iteritems():
            for loc, (real_av, flags) in flags4loc.iteritems():
                if Action.ACCEPTED not in flags:
                    continue
                pushid = push4action[flags[Action.ACCEPTED]]
                rv[av.code][loc] = revs[cs4push[pushid]][:12]

        print json.dumps(rv, indent=2, sort_keys=True)
