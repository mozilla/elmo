# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Status plugin to be used in buildbot masters serving the l10n dashboard.
'''
from __future__ import absolute_import

import os
import os.path

from buildbot.changes import base
from buildbot.status.base import StatusReceiverMultiService, StatusReceiver
from buildbot.scheduler import BaseScheduler
from twisted.python import log

from collections import defaultdict

# no imports of bb2mbdb code here, needs to be done after setting
# settings.py in os.environ in setupBridge

'''Buildbot StatusReceiver for bb2mbdb

The main entry point for buildbot status notifications are a
- fake scheduler to get all changes, and a
- StatusReceiver to get all builder.

Also add a fake ChangeSource, so that we can ensure the nextNumber
on ChangeMaster is set if we're resetting the master. That way, we don't
introduce conflicts with existing mbdb data.

Both are set up by calling into
 setupBridge()
so that you can pass in a single settings.py, and a BuildMasterConfig.
'''


def setupBridge(master, settings, config):
    '''Setup the bridget between buildbot and the database.

    This is also the closure in which all things happen that depend
    on the given settings.
    '''

    from bb2mbdb.utils import modelForSource, modelForChange, modelForLog, \
        timeHelper
    from mbdb.models import Master, Slave, Builder, BuildRequest, Build, Change

    dbm, new_master = Master.objects.get_or_create(name=master)

    class Scheduler(BaseScheduler):
        def addChange(self, change):
            dbchange = modelForChange(dbm, change)
            log.msg('ADDED CHANGE to DB, %d' % dbchange.number)

        def listBuilderNames(self):
            # Sadly, we need this. Buildbot is going to complain that we
            # don't build. What does he know.
            return []

    if 'schedulers' not in config:
        config['schedulers'] = []
    config['schedulers'].insert(0, Scheduler('bb2mbdb'))

    class ChangeSource(base.ChangeSource):
        '''Fake ChangeSource to sync ChangeMaster's nextNumber
        with mbdb.
        If mbdb is higher, set nextNumber and clear changes, ChangeMaster
        likely restarted from an unclean old state.
        Otherwise, we're fine, just let ChangeMaster do its thing. Also,
        mbdb might have gotten the last recent changes pruned by
        the clean_builds cron job.
        '''
        def startService(self):
            try:
                latest_changenumber = (
                    Change.objects
                    .order_by('-number')
                    .values_list('number', flat=True)[0]
                )
                if latest_changenumber >= self.parent.nextNumber:
                    self.parent.nextNumber = latest_changenumber + 1
                    del self.parent.changes[:]
                    log.msg('Resetting ChangeMaster.nextNumber')
                else:
                    log.msg('ChangeMaster.nextNumber is OK')
            except IndexError:
                log.msg('No changes in mbdb, leaving ChangeMaster alone')
                pass
    if 'change_source' not in config:
        config['change_source'] = []
    config['change_source'].insert(0, ChangeSource())

    class StepReceiver(StatusReceiver):
        '''Build- and StatusReceiver helper objects to receive all
        events for a particular step.
        '''
        def __init__(self, dbstep, basedir):
            self.step = dbstep
            self.basedir = basedir

        def stepTextChanged(self, build, step, text):
            self.step.text = text
            self.step.save()

        def stepText2Changed(self, build, step, text2):
            self.step.text2 = text2
            self.step.save()

        def logStarted(self, build, step, log):
            self.log = modelForLog(self.step, log, self.basedir)

        def logChunk(self, build, step, log, channel, text):
            pass

        def logFinished(self, build, step, log):
            self.log.isFinished = True
            self.log.save()
            pass

        def stepETAUpdate(self, build, step, ETA, expectations):
            '''TODO: ETA support.
            '''
            pass

    class BuildReceiver(StatusReceiver):
        '''StatusReceiver helper object to receive all events
        for a particular build.
        Caches the database model object.
        '''
        def __init__(self, dbbuild, basedir):
            self.build = dbbuild
            self.basedir = basedir
            self.latestStep = self.latestDbStep = None

        def stepStarted(self, build, step):
            self.latestStep = step
            starttime = timeHelper(step.getTimes()[0])
            self.latestDbStep = self.build.steps.create(name=step.getName(),
                                                        starttime=starttime,
                                                        text=step.getText(),
                                                        text2=step.text2)
            return StepReceiver(self.latestDbStep, self.basedir)

        def stepFinished(self, build, step, results):
            assert step == self.latestStep, "We lost a step somewhere"
            self.latestStep = None
            try:
                self.latestDbStep.endtime = timeHelper(step.getTimes()[1])
                # only the first is the result, the second is text2,
                # ignore that.
                self.latestDbStep.result = results[0]
                self.latestDbStep.text = step.getText()
                self.latestDbStep.text2 = step.text2
            except Exception as e:
                log.msg(str(e))
            self.latestDbStep.save()
            self.latestDbStep = None

        def buildETAUpdate(self, build, ETA):
            '''TODO: ETA support.
            '''
            pass

    class MyStatusReceiver(StatusReceiverMultiService):
        '''StatusReceiver for buildbot to db bridge.
        '''
        requestsForBuild = defaultdict(list)

        def setServiceParent(self, parent):
            StatusReceiverMultiService.setServiceParent(self, parent)
            self.setup()

        def setup(self):
            log.msg("mbdb subscribing")
            status = self.parent.getStatus()
            status.subscribe(self)

        def builderAdded(self, builderName, builder):
            log.msg("adding %s to mbdb" % builderName)
            try:
                dbbuilder = Builder.objects.get(master=dbm, name=builderName)
            except Builder.DoesNotExist:
                dbbuilder = Builder.objects.create(master=dbm,
                                                   name=builderName)
            dbbuilder.bigState = builder.getState()[0]
            if builder.category:
                dbbuilder.category = builder.category
            dbbuilder.save()
            log.msg("added %s to mbdb" % builderName)
            return self

        def requestSubmitted(self, request):
            b, _ = dbm.builders.get_or_create(name=request.getBuilderName())
            ss = modelForSource(dbm, request.source)
            submitTime = timeHelper(request.getSubmitTime())
            req = BuildRequest.objects.create(builder=b,
                                              submitTime=submitTime,
                                              sourcestamp=ss)

            def addBuild(build):
                dbbuild = b.builds.get(buildnumber=build.getNumber())
                dbbuild.requests.add(req)
            request.subscribe(addBuild)

        def builderChangedState(self, builderName, state):
            log.msg("%s changed state to %s" % (builderName, state))
            dbbuilder = Builder.objects.get(master=dbm, name=builderName)
            dbbuilder.bigState = state
            dbbuilder.save()

        def buildStarted(self, builderName, build):
            log.msg("build started on  %s" % builderName)
            builder = Builder.objects.get(master=dbm, name=builderName)
            slave, _ = Slave.objects.get_or_create(name=build.getSlavename())
            ss = modelForSource(dbm, build.getSourceStamp())
            starttime = timeHelper(build.getTimes()[0])
            dbbuild, created = \
                builder.builds.get_or_create(buildnumber=build.getNumber(),
                                             slave=slave,
                                             starttime=starttime,
                                             reason=build.getReason(),
                                             sourcestamp=ss)
            if not created:
                log.msg("%s build %d not created, endtime is %s" %
                        (builderName, build.getNumber(), dbbuild.endtime))
                log.msg("not watch this build, to make sure")
                return
            for key, value, source in build.getProperties().asList():
                dbbuild.setProperty(key, value, source)

            basedir = os.path.join(build.getBuilder().basedir, '..')

            return BuildReceiver(dbbuild, basedir)

        def buildFinished(self, builderName, build, results):
            log.msg("finished build on %s with %s" %
                    (builderName, str(results)))
            dbbuild = Build.objects.get(builder__name=builderName,
                                        buildnumber=build.getNumber())
            dbbuild.endtime = timeHelper(build.getTimes()[1])
            dbbuild.result = results
            dbbuild.save()
            for key, value, source in build.getProperties().asList():
                dbbuild.setProperty(key, value, source)
            pass

        def builderRemoved(self, builderName):
            log.msg("removing %s to mbdb" % builderName)
            # nothing to do here, afaict.
            pass

    if 'status' not in config:
        config['status'] = []
    config['status'].insert(0, MyStatusReceiver())
    log.msg("Done setting up Bridge")
