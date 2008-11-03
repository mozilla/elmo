from optparse import make_option
import pickle
import glob

from django.core.management.base import BaseCommand, CommandError
from mbdb.models import *
from django.conf import settings

class Command(BaseCommand):
    help = 'Import existing buildbot builds into the mbdb database'

    def handle(self, *args, **options):
        builderconfs = glob(settings.BUILDMASTER_BASE + '/*/builder')
        builderconfs.sort()
        for builderconf in buildernames:
            buildername = builderconf[len(settings.BUILDMASTER_BASE)+1:-8]
            if raw_input('Import %s? ' % buildername).lower() != 'y':
                print 'Skipping %s' % buildername
                continue
            try:
                firstBuild = int(raw_input('First build number: '))
            except ValueError:
                firstBuild = 1

            builder = pickle.load(open(builderconf))
            builder.basedir = builderconf[:-8]
            builder.determineNextBuildNumber()
            try:
                dbbuilder = Builder.objects.get(name = buildername)
            except:
                dbbuilder = Builder.objects.create(name = buildername,
                                                   category = builder.category,
                                                   bigState = builder.currentBigState)
                print "Created " + dbbuilder
            for buildnumber in xrange(firstBuild, builder.nextBuildNumber):
                try:
                    dbbuilder.builds.get(buildnumber = buildnumber)
                    print "Got build $d" % buildnumber
                    continue
                except:
                    pass
                build = builder.getBuild(buildnumber)
                dbbuild = dbbuilder.builds.create(buildnumber = buildnumber,
                                                  slavename = build.getSlavename(),
                                                  results = build.getResults(),
                                                  reason = build.getReason())
