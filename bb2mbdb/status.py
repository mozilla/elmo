# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n test automation.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation
# Portions created by the Initial Developer are Copyright (C) 2008
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#	Axel Hecht <l10n@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Status plugin to be used in buildbot masters serving the l10n dashboard.
'''

import os
import os.path

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

Both are set up by calling into 
 setupBridge()
so that you can pass in a single settings.py, and a BuildMasterConfig.
'''

# Notes on transaction handling:
# There are two patterns for the transaction handling in the status
# plugin below. Firstly, for methods that simply update the db, the
# handlers are decorated with @transation.commit_on_success. For
# handlers that attach new handlers, the decoration is
# @transition.commit_manually, and transaction.commit() is called after
# the child db objects is got, and before the child listener is created.

def setupBridge(master, settings, config):
    '''Setup the bridget between buildbot and the database.

    This is also the closure in which all things happen that depend
    on the given settings.
    '''

    # allow settings to be none for tests
    if settings is not None:
        os.environ['DJANGO_SETTINGS_MODULE'] = settings

    import bb2mbdb.utils
    reload(bb2mbdb.utils)
    import mbdb.models
    reload(mbdb.models)
    from bb2mbdb.utils import modelForSource, modelForChange, modelForLog, \
        timeHelper
    from mbdb.models import Master, Slave, Builder, BuildRequest, Build, \
        SourceStamp, NumberedChange

    from django.db import transaction

    try:
        # hack around the lack of @transaction.commit_manually
        transaction.enter_transaction_management()
        transaction.managed(True)
        dbm, new_master = Master.objects.get_or_create(name=master)
        transaction.commit()
    except:
        transaction.rollback()
        raise
    finally:
        transaction.leave_transaction_management()

    class Scheduler(BaseScheduler):
        @transaction.commit_on_success
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


    class StepReceiver(StatusReceiver):
        '''Build- and StatusReceiver helper objects to receive all
        events for a particular step.
        '''
        def __init__(self, dbstep, basedir):
            self.step = dbstep
            self.basedir = basedir

        @transaction.commit_on_success
        def stepTextChanged(self, build, step, text):
            self.step.text = text
            self.step.save()

        @transaction.commit_on_success
        def stepText2Changed(self, build, step, text2):
            self.step.text2 = text2
            self.step.save()

        @transaction.commit_on_success
        def logStarted(self, build, step, log):
            self.log = modelForLog(self.step, log, self.basedir)

        def logChunk(self, build, step, log, channel, text):
            pass

        @transaction.commit_on_success
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

        @transaction.commit_manually
        def stepStarted(self, build, step):
            self.latestStep = step
            self.latestDbStep = self.build.steps.create(name = step.getName(),
                                                        starttime = timeHelper(step.getTimes()[0]),
                                                        text = step.getText(),
                                                        text2 = step.text2)
            transaction.commit()
            return StepReceiver(self.latestDbStep, self.basedir)

        @transaction.commit_on_success
        def stepFinished(self, build, step, results):
            assert step == self.latestStep, "We lost a step somewhere"
            try:
                self.latestStep = None
                self.latestDbStep.endtime = timeHelper(step.getTimes()[1])
                # only the first is the result, the second is text2, ignore that.
                self.latestDbStep.result = results[0]
                self.latestDbStep.text = step.getText()
                self.latestDbStep.text2 = step.text2
                self.latestDbStep.save()
                self.latestDbStep = None
            except Exception, e:
                log.msg(str(e))
            pass

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

        @transaction.commit_on_success
        def builderAdded(self, builderName, builder):
            log.msg("adding %s to mbdb" % builderName)
            try:
                dbbuilder = Builder.objects.get(master=dbm, name = builderName)
            except Builder.DoesNotExist:
                dbbuilder = Builder.objects.create(master = dbm,
                                                   name = builderName)
            dbbuilder.bigState = builder.getState()[0]
            if builder.category:
                dbbuilder.category = builder.category
            dbbuilder.save()
            log.msg("added %s to mbdb" % builderName)
            return self

        @transaction.commit_manually
        def requestSubmitted(self, request):
            b, created = dbm.builders.get_or_create(name = request.getBuilderName())
            ss = modelForSource(dbm, request.source)
            req = BuildRequest.objects.create(builder = b,
                                              submitTime = timeHelper(request.getSubmitTime()),
                                              sourcestamp = ss)
            transaction.commit()
            def addBuild(build):
                dbbuild = b.builds.get(buildnumber=build.getNumber())
                dbbuild.requests.add(req)
                dbbuild.save()
            request.subscribe(addBuild)

        @transaction.commit_on_success
        def builderChangedState(self, builderName, state):
            log.msg("%s changed state to %s" % (builderName, state))
            dbbuilder = Builder.objects.get(master=dbm, name = builderName)
            dbbuilder.bigState = state
            dbbuilder.save()

        @transaction.commit_manually
        def buildStarted(self, builderName, build):
            log.msg("build started on  %s" % builderName)
            builder = Builder.objects.get(master=dbm, name = builderName)
            slave, newslave = Slave.objects.get_or_create(name = build.getSlavename())
            ss = modelForSource(dbm, build.getSourceStamp())
            dbbuild, created = \
                builder.builds.get_or_create(buildnumber = build.getNumber(),
                                             slave = slave,
                                             starttime = timeHelper(build.getTimes()[0]),
                                             reason = build.getReason(),
                                             sourcestamp = ss)
            if not created:
                log.msg("%s build %d not created, endtime is %s" %
                        (builderName, build.getNumber(), dbbuild.endtime))
                log.msg("not watch this build, to make sure")
                return
            for key, value, source in build.getProperties().asList():
                dbbuild.setProperty(key, value, source)
            dbbuild.save()
            transaction.commit()

            basedir = os.path.join(build.getBuilder().basedir, '..')

            return BuildReceiver(dbbuild, basedir)

        @transaction.commit_on_success
        def buildFinished(self, builderName, build, results):
            log.msg("finished build on %s with %s" % (builderName, str(results)))
            dbbuild = Build.objects.get(builder__name = builderName,
                                        buildnumber = build.getNumber())
            dbbuild.endtime = timeHelper(build.getTimes()[1])
            dbbuild.result = results
            for key, value, source in build.getProperties().asList():
                dbbuild.setProperty(key, value, source)
            dbbuild.save()
            pass

        def builderRemoved(self, builderName):
            log.msg("removing %s to mbdb" % builderName)
            # nothing to do here, afaict.
            pass

    if 'status' not in config:
        config['status'] = []
    config['status'].insert(0, MyStatusReceiver())
    log.msg("Done setting up Bridge")
