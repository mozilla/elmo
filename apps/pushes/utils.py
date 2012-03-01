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

'''Utility methods used by the twistd daemon and other hooks.
'''

from datetime import datetime
import os.path

from mercurial.hg import repository
from mercurial.ui import ui as _ui
from mercurial.error import RepoError
from mercurial.commands import pull, update, clone

from life.models import Repository, Push, Changeset, Branch, File
from django.conf import settings
from django.db import connection
from django.db import transaction


def getURL(repo, limit):
    lkp = repo.last_known_push()
    return '%sjson-pushes?startID=%d&endID=%d' % \
        (repo.url, lkp, lkp + limit)


class PushJS(object):
    def __init__(self, id, jsfrag):
        self.id = int(id)
        self.date = jsfrag['date']
        self.changesets = jsfrag['changesets']
        self.user = jsfrag['user']

    def __str__(self):
        return '<Push: %d>' % self.id


def getChangeset(repo, hgrepo, revision):
    try:
        cs = Changeset.objects.get(revision=revision)
        repo.changesets.add(cs)
        return cs
    except Changeset.DoesNotExist:
        pass
    # create the changeset, but first, let's see if we need the parents
    ctx = hgrepo.changectx(revision)
    parents = map(lambda _cx: _cx.hex(), ctx.parents())
    p_dict = dict(Changeset.objects
                  .filter(revision__in=parents)
                  .values_list('revision', 'id'))
    for p in parents:
        if p not in p_dict:
            p_cs = getChangeset(repo, hgrepo, p)
            p_dict[p_cs.revision] = p_cs.id
    cs = Changeset(revision=revision)
    cs.user = ctx.user().decode('utf-8', 'replace')
    cs.description = ctx.description().decode('utf-8', 'replace')
    branch = ctx.branch()
    if branch != 'default':
        # 'default' is already set in the db, only change if needed
        dbb, created = \
            Branch.objects.get_or_create(name=branch)
        cs.branch = dbb
    cs.save()
    cs.parents = p_dict.values()
    repo.changesets.add(cs, *(p_dict.values()))
    spacefiles = filter(lambda p: p.endswith(' '), ctx.files())
    goodfiles = filter(lambda p: not p.endswith(' '), ctx.files())
    if goodfiles:
        # chunk up the work on files,
        # mysql doesn't like them all at once
        chunk_count = len(goodfiles) / 1000 + 1
        chunk_size = len(goodfiles) / chunk_count
        if len(goodfiles) % chunk_size:
            chunk_size += 1
        for i in xrange(chunk_count):
            good_chunk = goodfiles[i * chunk_size:(i + 1) * chunk_size]
            existingfiles = File.objects.filter(path__in=good_chunk)
            existingpaths = existingfiles.values_list('path',
                                                      flat=True)
            existingpaths = dict.fromkeys(existingpaths)
            missingpaths = filter(lambda p: p not in existingpaths,
                                  good_chunk)
            cursor = connection.cursor()
            # XXX rv not checked, pyflakes complains. Probably rightfully so
            rv = cursor.executemany('INSERT INTO %s (path) VALUES (%%s)' %
                                    File._meta.db_table,
                                    map(lambda p: (p,), missingpaths))
            good_ids = File.objects.filter(path__in=good_chunk)
            cs.files.add(*list(good_ids.values_list('pk',
                                                    flat=True)))
    for path in spacefiles:
        # hack around mysql ignoring trailing ' ', and some
        # of our localizers checking in files with trailing ' '.
        f = filter(lambda fo: fo.path == path,
                   File.objects.filter(path=path))
        if f:
            cs.files.add(f[0])
        else:
            f = File.objects.create(path=path)
            cs.files.add(f)
            f.save()
    cs.save()
    return cs


@transaction.commit_manually
def handlePushes(repo_id, submits, do_update=True):
    if not submits:
        return
    repo = Repository.objects.get(id=repo_id)
    # XXX pyflakes complains, unused? needs tests before removal
    revisions = reduce(lambda r, l: r + l,
                       [p.changesets for p in submits],
       [])
    ui = _ui()
    repopath = os.path.join(settings.REPOSITORY_BASE,
                            repo.name)
    configpath = os.path.join(repopath, '.hg', 'hgrc')
    if not os.path.isfile(configpath):
        if not os.path.isdir(os.path.dirname(repopath)):
            os.makedirs(os.path.dirname(repopath))
        clone(ui, str(repo.url), str(repopath),
              pull=False, uncompressed=False, rev=[],
              noupdate=False)
        cfg = open(configpath, 'a')
        cfg.write('default-push = ssh%s\n' % str(repo.url)[4:])
        cfg.close()
        ui.readconfig(configpath)
        hgrepo = repository(ui, repopath)
    else:
        ui.readconfig(configpath)
        hgrepo = repository(ui, repopath)
        cs = submits[-1].changesets[-1]
        try:
            hgrepo.changectx(cs)
        except RepoError:
            pull(ui, hgrepo, source=str(repo.url),
                 force=False, update=False,
                 rev=[])
            if do_update:
                update(ui, hgrepo)
    for data in submits:
        changesets = []
        for revision in data.changesets:
            try:
                cs = getChangeset(repo, hgrepo, revision)
                transaction.commit()
                changesets.append(cs)
            except Exception, e:
                transaction.rollback()
                raise
                print repo.name, e
        p = Push.objects.create(repository=repo,
                                push_id=data.id, user=data.user,
                                push_date=datetime.utcfromtimestamp(data.date))
        p.changesets = changesets
        p.save()
        transaction.commit()
    repo.save()
    transaction.commit()
    return len(submits)
