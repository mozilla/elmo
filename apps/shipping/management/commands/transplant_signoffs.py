# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Bring sign-offs from a stable branch onto a project branch.
'''

from django.core.management.base import BaseCommand, CommandError
from shipping.models import AppVersion
from shipping.api import accepted_signoffs


class Command(BaseCommand):
    option_list = BaseCommand.option_list
    help = 'Transplant Signoffs and Actions from one appver to the other'
    args = 'old-appver new-appver'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("two arguments required, " +
                               "old and new appversion")
        old = AppVersion.objects.get(code=args[0])
        new = AppVersion.objects.get(code=args[1])
        if old.tree.l10n != new.tree.l10n:
            raise CommandError("Old and new appversion don't share l10n")
        sos = accepted_signoffs(id=old.id)
        for so in sos:
            print "transplanting " + so.locale.code
            _so = new.signoffs.create(push=so.push,
                                      author=so.author,
                                      when=so.when,
                                      locale=so.locale)
            for a in so.action_set.order_by('pk'):
                _so.action_set.create(flag=a.flag,
                                      author=a.author,
                                      when=a.when,
                                      comment=a.comment)
