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

import os

from buildbot.status.base import StatusReceiverMultiService
from buildbot.scheduler import BaseScheduler
from twisted.python import log

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

def setupBridge(settings, config):
    '''Setup the bridget between buildbot and the database.

    This is also the closure in which all things happen that depend
    on the given settings.
    '''

    os.environ['DJANGO_SETTINGS_MODULE'] = settings

    from bb2mbdb.utils import modelForChange, modelForLog, timeHelper

    class Scheduler(BaseScheduler):
        def addChange(self, change):
            dbchange = modelForChange(change)
            log.msg('ADDED CHANGE to DB, %d' % dbchange.number)
        def listBuilderNames(self):
            # Sadly, we need this. Buildbot is going to complain that we
            # don't build. What does he know.
            return []

    if 'schedulers' not in config:
        config['schedulers'] = []
    config['schedulers'].insert(0, Scheduler('bb2mbdb'))


    class StepReceiver(object):
        '''Build- and StatusReceiver helper objects to receive all
        events for a particular step.
        '''
        def __init__(self, dbstep):
            self.step = dbstep

        def logStarted(self, build, step, log):
            self.log = modelForLog(self.step, log)

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



    class BuildReceiver(object):
        '''StatusReceiver helper object to receive all events
        for a particular build.
        Caches the database model object.
        '''
        def __init__(self, dbbuild):
            self.build = dbbuild
            self.latestStep = self.latestDbStep = None

        def stepStarted(self, build, step):
            self.latestStep = step
            self.latestDbStep = self.build.steps.create(name = step.getName(),
                                                        starttime = timeHelper(step.getTimes()[0]),
                                                        text = ' '.join(step.getText()),
                                                        text2 = ' '.join(step.text2))
            return StepReceiver(self.latestDbStep)

        def stepFinished(self, build, step, results):
            assert step == self.latestStep, "We lost a step somewhere"
            self.latestStep = None
            self.latestDbStep.endtime = timeHelper(step.getTimes()[1])
            self.latestDbStep.result = results
            self.latestDbStep.save()
            self.latestDbStep = None
            pass

        def buildETAUpdate(self, build, ETA):
            '''TODO: ETA support.
            '''
            pass

            

    class StatusReceiver(StatusReceiverMultiService):
        '''StatusReceiver for buildbot to db bridge.
        '''
        def builderAdded(self, builderName, builder):
            try:
                dbbuilder = Builder.objects.get(name = builderName)
            except Builder.DoesNotExist:
                dbbuilder = Builder.objects.create(name = builderName)
            dbbuilder.bigState = builder.getState()[0]
            if builder.category:
                dbbuilder.category = builder.category
            dbbuilder.save()

        def builderChangedState(self, builderName, state):
            dbbuilder = Builder.objects.get(name = builderName)
            dbbuilder.bigState = state
            dbbuilder.save()

        def buildStarted(self, builderName, build):
            dbbuilder = Builder.objects.get(name = builderName)
            dbbuild = dbbuilder.builds.create(buildnumber = build.getNumber(),
                                              slavename = build.getSlavename(),
                                              starttime = timeHelper(build.getTimes()[0]),
                                              reason = build.getReason())
            for key, value, source in build.getProperties().asList():
                dbbuild.setProperty(key, value, source)
            for change in build.getChanges():
                dbbuild.changes.add(utils.modelForChange(change))
            dbbuild.save()

            return BuildReceiver(dbbuild)

        def buildFinished(self, builderName, build, results):
            dbbuild = Build.objects.get(builder__name = builderName,
                                        buildnumber = build.getNumber())
            dbbuild.endtime = timeHelper(build.getTimes()[1])
            dbbuild.result = results
            for key, value, source in build.getProperties().asList():
                dbbuild.setProperty(key, value, source)
            pass

        def builderRemoved(self, builderName):
            # nothing to do here, afaict.
            pass

    if 'status' not in config:
        config['status'] = []
    config['status'].insert(0, StatusReceiver())
