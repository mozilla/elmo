# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Utility methods used by the twistd daemon and other hooks.
'''

from datetime import datetime
import os.path
from mercurial.hg import repository
from mercurial.ui import ui
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


def get_or_create_changeset(repo, hgrepo, revision):
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
            p_cs = get_or_create_changeset(repo, hgrepo, p)
            p_dict[p_cs.revision] = p_cs.id
    cs = Changeset(revision=revision)
    cs.user = ctx.user().decode('utf-8', 'replace')
    cs.description = ctx.description().decode('utf-8', 'replace')
    branch = ctx.branch()
    if branch != 'default':
        # 'default' is already set in the db, only change if needed
        dbb, __ = Branch.objects.get_or_create(name=branch)
        cs.branch = dbb

    # because the many-to-many relationships etc don't work until the object
    # has an ID
    cs.save()

    cs.parents = p_dict.values()
    repo.changesets.add(cs, *(p_dict.values()))
    spacefiles = [p for p in ctx.files() if p.endswith(' ')]
    goodfiles = [p for p in ctx.files() if not p.endswith(' ')]
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
            cursor.executemany('INSERT INTO %s (path) VALUES (%%s)' %
                               File._meta.db_table,
                               map(lambda p: (p,), missingpaths))
            good_ids = File.objects.filter(path__in=good_chunk)
            cs.files.add(*list(good_ids.values_list('pk', flat=True)))
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


@transaction.commit_on_success
def handlePushes(repo_id, submits, do_update=True):
    if not submits:
        return
    repo = Repository.objects.get(id=repo_id)
    hgrepo = _hg_repository_sync(repo.name, repo.url, submits,
                                 do_update=do_update)
    for data in submits:
        changesets = []
        for revision in data.changesets:
            cs = get_or_create_changeset(repo, hgrepo, revision)
            changesets.append(cs)
        p, __ = Push.objects.get_or_create(
          repository=repo,
          push_id=data.id, user=data.user,
          push_date=datetime.utcfromtimestamp(data.date)
        )
        p.changesets = changesets
        p.save()
    repo.save()
    return len(submits)


def _hg_repository_sync(name, url, submits, do_update=True):
    ui_ = ui()
    repopath = os.path.join(settings.REPOSITORY_BASE, name)
    configpath = os.path.join(repopath, '.hg', 'hgrc')
    if not os.path.isfile(configpath):
        if not os.path.isdir(os.path.dirname(repopath)):
            os.makedirs(os.path.dirname(repopath))
        clone(ui_, str(url), str(repopath),
              pull=False, uncompressed=False, rev=[],
              noupdate=False)
        cfg = open(configpath, 'a')
        cfg.write('default-push = ssh%s\n' % str(url)[4:])
        cfg.close()
        ui_.readconfig(configpath)
        hgrepo = repository(ui_, repopath)
    else:
        ui_.readconfig(configpath)
        hgrepo = repository(ui_, repopath)
        cs = submits[-1].changesets[-1]
        try:
            hgrepo.changectx(cs)
        except RepoError:
            pull(ui_, hgrepo, source=str(url),
                 force=False, update=False,
                 rev=[])
            if do_update:
                # Make sure that we're not triggering workers in post 2.6
                # hg. That's not stable, at least as we do it.
                # Monkey patch time
                try:
                    from mercurial import worker
                    if hasattr(worker, '_startupcost'):
                        # use same value as hg for non-posix
                        worker._startupcost = 1e30
                except ImportError:
                    # no worker, no problem
                    pass
                update(ui_, hgrepo)
    return hgrepo
