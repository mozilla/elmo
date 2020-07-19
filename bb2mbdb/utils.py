# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Utility and help code for buildbot-mbdb adapters.'''
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import datetime
import os.path

from mbdb.models import Change, Tag, File, SourceStamp
from django.db import transaction
import six


def timeHelper(t):
    if t is None:
        return t
    return datetime.utcfromtimestamp(t)


@transaction.atomic
def modelForChange(main, change):
    try:
        dbchange = Change.objects.get(main=main, number=change.number)
        return dbchange
    except Change.DoesNotExist:
        dbchange = Change.objects.create(main=main, number=change.number,
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
        newfiles = set(change.files) - set((six.text_type(f) for f in dbfiles))
        dbfiles += [File.objects.create(path=file) for file in newfiles]
        dbchange.files.add(*dbfiles)
        return dbchange


@transaction.atomic
def modelForSource(main, source, maxChanges=4):
    '''Get a db model for a buildbot SourceStamp.

    main is the db model for the buildbot main, source is the
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
        q = q.filter(numbered_changes__change__main=main)
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
            if cs == [change.number for change in source.changes[maxChanges:]]:
                return ss

    # create a new source stamp.
    ss = SourceStamp.objects.create(branch=source.branch,
                                    revision=source.revision)
    for i, change in enumerate(source.changes):
        cm = modelForChange(main, change)
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
