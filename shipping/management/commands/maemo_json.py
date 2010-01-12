from optparse import make_option
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from shipping.models import Milestone, AppVersion
from shipping.views import _signoffs
from life.models import Changeset

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-a', '--app-version', dest = 'appver',
                    help = 'AppVersion to get signoffs for'),
        make_option('-m', '--milestone', dest = 'ms',
                    help = 'Milestone to get signoffs for'),
        )
    help = 'Create a l10n-changesets file for maemo'
    args = 'maemo-locales'

    def handle(self, *args, **options):
        appver = options.get('appver', None)
        if appver is None:
            ms = options.get('ms', None)
            if ms is not None:
                av_or_m = Milestone.objects.get(code=ms)
        else:
            av_or_m = AppVersion.objects.get(code=appver)
        if not args or av_or_m is None:
            return
        sos = _signoffs(av_or_m).annotate(tip=Max('push__changesets__id'))
        tips = dict(sos.values_list('locale__code', 'tip'))
        revmap = dict(Changeset.objects.filter(id__in=tips.values()).values_list('id', 'revision'))
        multi = map(lambda s: s.strip(), open(args[0]).readlines())
        chunks = []
        for loc in sorted(tips.keys()):
            platforms = ['"maemo"']
            if loc in multi:
                platforms.append('"maemo-multilocale"')
            platforms = ', '.join(platforms)
            chunks.append('''  "%(loc)s": {
    "revision": "%(rev)s",
    "platforms": [%(plat)s]
  }''' % {"loc":loc, "rev":revmap[tips[loc]][:12], "plat": platforms})
        out = "{\n%s\n}" % ",\n".join(chunks)
        print out
