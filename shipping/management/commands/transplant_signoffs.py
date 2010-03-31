from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from shipping.models import AppVersion
from shipping.views import _signoffs
import pdb

class Command(BaseCommand):
    option_list = BaseCommand.option_list
    help = 'Transplant Signoffs and Actions from one appver to the other'
    args = 'old-appver new-appver'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError, "two arguments required, old and new appversion"
        old = AppVersion.objects.get(code=args[0])
        new = AppVersion.objects.get(code=args[1])
        if old.tree.l10n != new.tree.l10n:
            raise CommandError, "Old and new appversion don't share l10n"
        sos = _signoffs(old)
        for so in sos:
            print "transplanting " + so.locale.code
            _so = new.signoffs.create(push = so.push,
                                      author = so.author,
                                      when = so.when,
                                      locale = so.locale)
            for a in so.action_set.order_by('pk'):
                _so.action_set.create(flag = a.flag,
                                      author = a.author,
                                      when = a.when,
                                      comment = a.comment)
