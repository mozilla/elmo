from optparse import make_option
import os.path

from django.core.management.base import BaseCommand, CommandError
from pushes.models import *
from mbdb.models import *
from django.conf import settings

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest = 'quiet', action = 'store_true',
                    help = 'Run quietly'),
        )
    help = 'Verify a l10n-changesets file'
    args = 'l10n-changesets'

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        if not args:
            return
        for line in open(args[0]).readlines():
            line = line.strip()
            locale, revision = line.split()
            revision = revision[:12]
            try:
                p = Property.objects.get(name = 'l10n_revision',
                                         value = revision)
                lp = Property.objects.filter(name = 'locale',
                                             value = locale)
                blds = Build.objects.filter(properties=p)
                blds = blds.filter(properties__in = lp)
                blds = blds.order_by('-pk')
                print "found %d builds for %s" % (blds.count(), locale)
            except Exception, e:
                print "no build for %s, %s" % (locale, e)
