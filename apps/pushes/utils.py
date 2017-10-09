# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Utility methods used by the twistd daemon and other hooks.
'''
from __future__ import absolute_import, division

from datetime import datetime
import json
import os.path
import urllib2
import hglib

from life.models import Repository, Push, Changeset, Branch, File
from django.conf import settings
from django.db import transaction, connection
from six.moves import range


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


def get_or_create_changeset(repo, hgrepo, ctx):
    try:
        cs = Changeset.objects.get(revision=ctx.node())
        repo.changesets.add(cs)
        return cs
    except Changeset.DoesNotExist:
        pass
    # create the changeset, but first, let's see if we need the parents
    parent_revs = [parent.node() for parent in ctx.parents()]
    p_dict = dict(Changeset.objects
                  .filter(revision__in=parent_revs)
                  .values_list('revision', 'id'))
    for p in ctx.parents():
        if p.node() not in p_dict:
            p_cs = get_or_create_changeset(repo, hgrepo, p)
            p_dict[p_cs.revision] = p_cs.id
    cs = Changeset(revision=ctx.node())
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

    cs.parents.set(list(p_dict.values()))
    repo.changesets.add(cs, *(list(p_dict.values())))
    spacefiles = [p for p in ctx.files() if p.endswith(' ')]
    goodfiles = [p for p in ctx.files() if not p.endswith(' ')]
    if goodfiles:
        # chunk up the work on files,
        # mysql doesn't like them all at once
        chunk_count = len(goodfiles) // 1000 + 1
        chunk_size = len(goodfiles) // chunk_count
        if len(goodfiles) % chunk_size:
            chunk_size += 1
        for i in range(chunk_count):
            good_chunk = goodfiles[i * chunk_size:(i + 1) * chunk_size]
            existingfiles = File.objects.filter(path__in=good_chunk)
            existingpaths = existingfiles.values_list('path',
                                                      flat=True)
            existingpaths = dict.fromkeys(existingpaths)
            missingpaths = [p for p in good_chunk if p not in existingpaths]
            File.objects.bulk_create([
                File(path=p)
                for p in missingpaths
            ])
            good_ids = File.objects.filter(path__in=good_chunk)
            cs.files.add(*list(good_ids.values_list('pk', flat=True)))
    for path in spacefiles:
        # hack around mysql ignoring trailing ' ', and some
        # of our localizers checking in files with trailing ' '.
        f = [fo for fo in File.objects.filter(path=path) if fo.path == path]
        if f:
            cs.files.add(f[0])
        else:
            f = File.objects.create(path=path)
            cs.files.add(f)
            f.save()
    cs.save()
    return cs


def handlePushes(repo_id, submits, do_update=False, close_connection=False):
    if close_connection:
        # maybe we lost the connection, close it to make sure we get a new one
        connection.close()
    repo = Repository.objects.get(id=repo_id)
    hgrepo = _hg_repository_sync(repo.local_path(), repo.url,
                                 do_update=do_update)
    revs = reduce(
        lambda r, l: r+l,
        (data.changesets for data in submits),
        [])
    if not revs:
        r = urllib2.urlopen(repo.url + u'json-log?rev=head()')
        data = json.load(r)
        revs += [d['node'] for d in data['entries']]
        if not revs:
            revs.append(data['node'])
    rev_to_changeset = {}
    for revision in revs:
        rev_to_changeset[revision] = \
            get_or_create_changeset(repo, hgrepo, hgrepo[revision])
    # roll the complete push into one transaction, with all the jazz
    # about changesets and files and etc.
    with transaction.atomic():
        for data in submits:
            changesets = [rev_to_changeset[rev] for rev in data.changesets]
            p, __ = Push.objects.get_or_create(
              repository=repo,
              push_id=data.id, user=data.user,
              push_date=datetime.utcfromtimestamp(data.date)
            )
            p.changesets.set(changesets)
            p.save()
        repo.save()
    hgrepo.close()
    return len(submits)


def _hg_repository_sync(repopath, url, do_update=False):
    configpath = os.path.join(repopath, '.hg', 'hgrc')
    if not os.path.isfile(configpath):
        if not os.path.isdir(os.path.dirname(repopath)):
            os.makedirs(os.path.dirname(repopath))
        hgrepo = hglib.clone(source=str(url), dest=str(repopath))
        cfg = open(configpath, 'a')
        cfg.write('default-push = ssh%s\n' % str(url)[4:])
        cfg.close()
        hgrepo.open()
    else:
        hgrepo = hglib.open(repopath)
        hgrepo.pull(source=str(url))
        if do_update:
            hgrepo.update()
    return hgrepo
