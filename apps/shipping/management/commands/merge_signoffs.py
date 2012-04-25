# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Bring back together sign-offs from a project branch with those from the
stable branch.
'''

from django.core.management.base import BaseCommand, CommandError
from shipping.models import AppVersion
from shipping.api import accepted_signoffs


class Command(BaseCommand):
    option_list = BaseCommand.option_list
    help = """Merge Signoffs (and Actions) from one appver to the other

Only recreates those sign-offs that don't exist on the target appver."""
    args = 'forked-appver target-appver'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("two arguments required, " +
                               "old and new appversion")
        fork = AppVersion.objects.get(code=args[0])
        target = AppVersion.objects.get(code=args[1])
        if fork.tree.l10n != target.tree.l10n:
            raise CommandError("Fork and target appversion don't share l10n")
        fsos = accepted_signoffs(id=fork.id)
        tsos = accepted_signoffs(id=target.id)
        known_push_ids = dict(tsos.values_list('locale__code', 'push__id'))
        sos = fsos.exclude(push__id__in=known_push_ids.values())

        for so in sos.order_by('locale__code').select_related('locale'):
            if so.push_id <= known_push_ids[so.locale.code]:
                print "not merging %s, target newer" % so.locale.code
                continue
            print "merging " + so.locale.code
            _so = target.signoffs.create(push=so.push,
                                      author=so.author,
                                      when=so.when,
                                      locale=so.locale)
            for a in so.action_set.order_by('pk'):
                _so.action_set.create(flag=a.flag,
                                      author=a.author,
                                      when=a.when,
                                      comment=a.comment)
