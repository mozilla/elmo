from optparse import make_option
import pickle
from glob import glob

from django.core.management.base import BaseCommand, CommandError
from mbdb.models import *
from adapter import utils
from django.conf import settings

class Command(BaseCommand):
    help = 'Import existing buildbot builds into the mbdb database'

    def handle(self, *args, **options):
        builderconfs = glob(settings.BUILDMASTER_BASE + '/*/builder')
        builderconfs.sort()
        for builderconf in builderconfs:
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
                print "Created %s" % dbbuilder
            for buildnumber in xrange(firstBuild, builder.nextBuildNumber):
                print buildnumber
                try:
                    dbbuilder.builds.get(buildnumber = buildnumber)
                    print "Got build $d" % buildnumber
                    continue
                except:
                    pass
                build = builder.getBuild(buildnumber)
                times = map(utils.timeHelper, build.getTimes())
                dbbuild = dbbuilder.builds.create(buildnumber = buildnumber,
                                                  slavename = build.getSlavename(),
                                                  starttime = times[0],
                                                  endtime = times[1],
                                                  result = build.getResults(),
                                                  reason = build.getReason())
                for key, value, source in build.getProperties().asList():
                    dbbuild.setProperty(key, value, source)
                for change in build.getChanges():
                    dbbuild.changes.add(utils.modelForChange(change))
                cutoff = len(settings.BUILDMASTER_BASE)+1
                for step in build.getSteps():
                    times = map(utils.timeHelper, step.getTimes())
                    if times[1] is None:
                        #step is still running or never run, no result
                        result = None
                    else:
                        result = step.getResults()[0]
                    dbstep = dbbuild.steps.create(name = step.getName(),
                                                  text = " ".join(step.getText()),
                                                  starttime = times[0],
                                                  endtime = times[1],
                                                  result = result)
                    for logfile in step.getLogs():
                        if not hasattr(logfile, 'getFilename'):
                            dbstep.logs.create(filename = None,
                                               html = logfile.html,
                                               isFinished = True)
                        else:
                            relfile = logfile.getFilename()[cutoff:]
                            dbstep.logs.create(filename = relfile,
                                               html = None,
                                               isFinished = True)
                dbbuild.save()
