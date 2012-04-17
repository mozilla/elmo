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
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
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

'''Utility and help code for buildbot-mbdb adapters.'''


from datetime import datetime
import os.path

from mbdb.models import Change, Tag, File, SourceStamp


def timeHelper(t):
    if t is None:
        return t
    return datetime.utcfromtimestamp(t)


def modelForChange(master, change):
    try:
        dbchange = Change.objects.get(master=master, number=change.number)
        return dbchange
    except Change.DoesNotExist:
        dbchange = Change.objects.create(master=master, number=change.number,
                                         when=timeHelper(change.when))
        for prop in ('branch', 'revision', 'who', 'comments'):
            val = getattr(change, prop)
            if val:
                setattr(dbchange, prop, val)
        if hasattr(change, 'locale'):
            tag, created = Tag.objects.get_or_create(value=change.locale)
            dbchange.tags.add(tag)
        dbchange.save()
        if not change.files:
            return dbchange

        dbfiles = list(File.objects.filter(path__in=change.files))
        newfiles = set(change.files) - set(map(unicode, dbfiles))
        dbfiles += [File.objects.create(path=file) for file in newfiles]
        dbchange.files.add(*dbfiles)
        dbchange.save()
        return dbchange


def modelForSource(master, source, maxChanges=4):
    '''Get a db model for a buildbot SourceStamp.

    master is the db model for the buildbot master, source is the
    buildbot SourceStamp object.
    Optional argument maxChanges limits how many changes are part
    of the db query. All changes will be checked, this is just
    to limit the query complexity in the rare case of tons of changes
    per source stamp. sqlite seems to have a limit of 64, let's be well
    below that by default.
    '''
    q = SourceStamp.objects.filter(branch=source.branch,
                                   revision=source.revision)
    if len(source.changes):
        q = q.filter(numbered_changes__change__master=master)
    for i, change in enumerate(source.changes[:maxChanges]):
        q = q.filter(numbered_changes__number=i,
                     numbered_changes__change__number=change.number)

    if len(source.changes) < maxChanges:
        # all change numbers are in the query, make sure we don't have more
        # and just pick the first
        for ss in q:
            if ss.changes.count() == len(source.changes):
                return ss
    else:
        # we have more changes than in the query, if we find one
        # with the right change numbers, pick that
        for ss in q:
            cs = ss.numbered_changes.order_by('number')[maxChanges:]
            cs = list(cs.values_list('change__number', flat=True))
            if cs == map(lambda change: change.number,
                         source.changes[maxChanges:]):
                return ss

    # create a new source stamp.
    ss = SourceStamp.objects.create(branch=source.branch,
                                    revision=source.revision)
    for i, change in enumerate(source.changes):
        cm = modelForChange(master, change)
        ss.numbered_changes.create(change=cm, number=i)
    ss.save()
    return ss


def modelForLog(dbstep, logfile, basedir, isFinished=False):
    if not hasattr(logfile, 'getFilename'):
        logf = dbstep.logs.create(filename=None, html=logfile.html,
                                  name=logfile.getName(),
                                  isFinished=True)
    else:
        relfile = os.path.relpath(logfile.getFilename(), basedir)
        logf = dbstep.logs.create(filename=relfile, html=None,
                                  name=logfile.getName(),
                                  isFinished=isFinished)
    return logf
