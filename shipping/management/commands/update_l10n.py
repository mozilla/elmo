from optparse import make_option
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from shipping.models import Milestone
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

        sos=dict(ms.signoffs.values_list('locale__code', 'push_id'))
        tips = dict(Push.objects.filter(id__in=sos.values()).annotate(tip=Max('changesets__id')).values_list('id', 'tip'))
        revs = dict(Changeset.objects.filter(id__in=tips.values()).values_list('id','revision'))
        from mercurial.dispatch import dispatch as hgdispatch
        for loc in sorted(sos.keys()):
            repopath = resolve(loc)
            rev = revs[tips[sos[loc]]]
            hgdispatch(['update', '-R', repopath, '-r', rev])
