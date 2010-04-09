from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from shipping.models import AppVersion
from shipping.views import _signoffs
import pdb

class Command(BaseCommand):
    option_list = BaseCommand.option_list
    help = '''Merge Signoffs (and Actions) from one appver to the other

Only recreates those sign-offs that don't exist on the target appver.'''
    args = 'forked-appver target-appver'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError, "two arguments required, old and new appversion"
        fork = AppVersion.objects.get(code=args[0])
        target = AppVersion.objects.get(code=args[1])
        if fork.tree.l10n != target.tree.l10n:
            raise CommandError, "Fork and target appversion don't share l10n"
        fsos = _signoffs(fork)
        tsos = _signoffs(target)
        known_push_ids = tsos.values_list('push__id', flat=True)
        sos = fsos.exclude(push__id__in=known_push_ids)
        
        for so in sos:
            print "merging " + so.locale.code
            _so = target.signoffs.create(push = so.push,
                                      author = so.author,
                                      when = so.when,
                                      locale = so.locale)
            for a in so.action_set.order_by('pk'):
                _so.action_set.create(flag = a.flag,
                                      author = a.author,
                                      when = a.when,
                                      comment = a.comment)
