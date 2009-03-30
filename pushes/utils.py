from datetime import datetime
import os.path
try:
    import json
except ImportError:
    import simplejson as json

from mercurial.hg import repository
from mercurial.ui import ui as _ui
from mercurial.commands import pull, update, clone

from pushes.models import Push, Changeset, File
from django.conf import settings

def getURL(repo, limit):
    return '%sjson-pushes?startID=%d&endID=%d' % \
        (repo.url, repo.last_known_push, repo.last_known_push + limit)

def handlePushes(page, repo, do_update=True):
    pushes = json.loads(page)
    if not pushes:
        return
    revisions = reduce(lambda r,l: r+l,
                       [p['changesets'] for p in pushes.values()],
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
        pull(ui, hgrepo, source = str(repo.url),
             force=False, update=False,
             rev=[])
        if do_update:
            update(ui, hgrepo)
    id = repo.last_known_push
    ids = pushes.keys()
    ids.sort(lambda l,r: cmp(int(l), int(r)))
    for id in ids:
        data = pushes[id]
        p = Push(push_id = int(id),
                 user = data['user'],
                 repository = repo,
                 push_date = datetime.utcfromtimestamp(data['date']))
        p.save()
        for revision in data['changesets']:
            cs = Changeset(push = p, revision = revision)
            try:
                ctx = hgrepo.changectx(cs.revision)
                cs.user = ctx.user().decode('utf-8', 'replace')
                cs.description = ctx.description().decode('utf-8', 'replace')
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
    repo.last_known_push = int(id)
    repo.save()
