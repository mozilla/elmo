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
        p = Push(push_id = data.id,
                 user = data.user,
                 repository = repo,
                 push_date = datetime.utcfromtimestamp(data.date))
        p.save()
        for revision in data.changesets:
            cs = Changeset(push = p, revision = revision)
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
                for path in ctx.files():
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
            except Exception, e:
                print repo.name, e
            cs.save()
    repo.save()
    return len(submits)
