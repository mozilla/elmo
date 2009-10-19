from datetime import datetime
import os.path
try:
    import json
except ImportError:
    import simplejson as json

from mercurial.hg import repository
from mercurial.ui import ui as _ui
try:
    from mercurial.repo import RepoError
except ImportError:
    from mercurial.error import RepoError
from mercurial.commands import pull, update, clone

from pushes.models import Repository, Push, Changeset, Branch, File
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

@transaction.commit_manually
def handlePushes(repo_id, submits, do_update=True):
    if not submits:
        return
    repo = Repository.objects.get(id=repo_id)
    revisions = reduce(lambda r,l: r+l,
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
            pull(ui, hgrepo, source = str(repo.url),
                 force=False, update=False,
                 rev=[])
            if do_update:
                update(ui, hgrepo)
    for data in submits:
        changesets = []
        for revision in data.changesets:
            cs, created = Changeset.objects.get_or_create(repository = repo,
                                                          revision = revision)
            changesets.append(cs)
            if not created:
                continue
            try:
                ctx = hgrepo.changectx(cs.revision)
                cs.user = ctx.user().decode('utf-8', 'replace')
                cs.description = ctx.description().decode('utf-8', 'replace')
                branch = ctx.branch()
                if branch != 'default':
                    # 'default' is already set in the db, only change if needed
                    dbb, created = \
                        Branch.objects.get_or_create(name=branch)
                    cs.branch = dbb
                cs.save()
                parents = map(lambda _cx: _cx.hex(), ctx.parents())
                p_cs = Changeset.objects.filter(revision__in=parents,
                                                repository=repo)
                cs.parents.add(*list(p_cs))
                cs.save()
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
                        good_chunk = goodfiles[i*chunk_size:(i+1)*chunk_size]
                        existingfiles = File.objects.filter(path__in=good_chunk)
                        existingpaths = existingfiles.values_list('path',
                                                                  flat=True)
                        existingpaths = dict.fromkeys(existingpaths)
                        missingpaths = filter(lambda p: p not in existingpaths,
                                              good_chunk)
                        cursor = connection.cursor()
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
                               File.objects.filter(path = path))
                    if f:
                        cs.files.add(f[0])
                    else:
                        f = File.objects.create(path = path)
                        cs.files.add(f)
                        f.save()
                cs.save()
                transaction.commit()
            except Exception, e:
                transaction.rollback()
                raise
                print repo.name, e
        p = Push.objects.create(push_id = data.id, user = data.user,
                                push_date =
                                datetime.utcfromtimestamp(data.date))
        p.changesets = changesets
        transaction.commit()
    repo.save()
    transaction.commit()
    return len(submits)
