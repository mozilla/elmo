from optparse import make_option
import pickle
from glob import glob

from django.core.management.base import BaseCommand, CommandError
from mbdb.models import *
from bb2mbdb import utils
from django.conf import settings

def iterOverBuilds(builder, dbbuilder, buildername, start):
    for i in xrange(start, builder.nextBuildNumber):
        yield {'buildername' : buildername,
               'buildnumber' : i,
               'build'       : builder.getBuild(i),
               'builder'     : builder,
               'dbbuilder'   : dbbuilder}


class Command(BaseCommand):
    help = 'Import existing buildbot builds into the mbdb database'

    def handle(self, *args, **options):
        builderconfs = glob(settings.BUILDMASTER_BASE + '/*/builder')
        builderconfs.sort()
        builders = []
        for builderconf in builderconfs:
            buildername = builderconf[len(settings.BUILDMASTER_BASE)+1:-8]
            if raw_input('Import %s? ' % buildername).lower() != 'y':
                print 'Skipping %s' % buildername
                continue
            builder = pickle.load(open(builderconf))
            builder.basedir = builderconf[:-8]
            builder.determineNextBuildNumber()
            if buildername != builder.getName():
                print '%s is %s in reality' % (buildername, builder.getName())
                buildername = builder.getName()
            try:
                dbbuilder = Builder.objects.get(name = buildername)
                q = dbbuilder.builds.order_by('-pk').values_list('buildnumber', flat=True)
                if q.count():
                    firstBuild = q[0] + 1
                else:
                    firstBuild = 0
            except:
                dbbuilder = Builder.objects.create(name = buildername,
                                                   category = builder.category,
                                                   bigState = builder.currentBigState)
                firstBuild = 0
                print "Created %s" % dbbuilder
            try:
                firstBuild = int(raw_input('First build number (%d): ' % firstBuild))
            except ValueError:
                pass
            g = iterOverBuilds(builder, dbbuilder, buildername, firstBuild)
            try:
                localvars = g.next()
            except StopIteration:
                print "no more builds for %s" % buildername
                continue
            builders.append([g, localvars])

        while builders:
            # pick the earliest available build
            builders.sort(lambda l, r: cmp(l[1]['build'].getTimes()[0],
                                           r[1]['build'].getTimes()[0]))
            localvars = builders[0][1]
            try:
                builders[0][1] = builders[0][0].next()
            except StopIteration:
                # builder is exhausted, drop it from the list.
                # this is basically the end condition for the loop
                builders.pop(0)
            buildername = localvars['buildername']
            builder = localvars['builder']
            dbbuilder = localvars['dbbuilder']
            buildnumber = localvars['buildnumber']
            print buildername, buildnumber
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
            for step in build.getSteps():
                times = map(utils.timeHelper, step.getTimes())
                if times[1] is None:
                    #step is still running or never run, no result
                    result = None
                else:
                    result = step.getResults()[0]
                dbstep = dbbuild.steps.create(name = step.getName(),
                                              text = step.getText(),
                                              text2 = step.text2,
                                              starttime = times[0],
                                              endtime = times[1],
                                              result = result)
                for logfile in step.getLogs():
                    utils.modelForLog(dbstep, logfile, isFinished = True)
            dbbuild.save()
