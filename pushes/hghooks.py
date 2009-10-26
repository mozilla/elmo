from datetime import datetime
import re
import os

from django.conf import settings

if not settings.configured:
    from l10n_site import local_settings
    d = dict(local_settings.__dict__)
    d['INSTALLED_APPS'] = ['life', 'pushes']
    settings.configure(**d)

from django.db import transaction
from life.models import Repository, Forest, Push
from pushes.utils import getChangeset

@transaction.commit_manually
def add_push(ui, repo, node, **kwargs):
    try:
        # all changesets from node to 'tip' inclusive are part of this push
        topdir = ui.config('pushes','topdir').split('/')
        baseurl = ui.config('pushes','baseurl')
        repo_name = repo.path.split('/') # XXX os.sep?
        while topdir and topdir[0] == repo_name[0]:
            topdir.pop(0)
            repo_name.pop(0)
        if repo_name[-1] == '.hg':
            repo_name.pop()
        repo_name = '/'.join(filter(None, repo_name))
        url = baseurl + repo_name + '/'
        dbrepo, _created = Repository.objects.get_or_create(name = repo_name,
                                                            url = url)
        # figure out forest
        for _section, pattern in ui.configitems('pushes_forests'):
            m = re.match(pattern, repo_name)
            if m is None:
                continue
            f_url = baseurl + m.group() + '/'
            forest, _created = Forest.objects.get_or_create(name = m.group(),
                                                            url = f_url)
            dbrepo.forest = forest
            dbrepo.save()
            break
        changesets = []
        rev = repo.changectx(node).rev()
        tip = repo.changectx('tip').rev()
        for i in range(rev, tip+1):
            ctx = repo.changectx(i)
            cs = getChangeset(dbrepo, repo, ctx.hex())
            transaction.commit()
            changesets.append(cs)
        p = Push.objects.create(repository=dbrepo,
                                push_id = dbrepo.last_known_push() + 1,
                                push_date = datetime.utcnow(),
                                user = os.environ['USER'])
        p.changesets = changesets
        p.save()
        transaction.commit()
        return 0
    except Exception, e:
        transaction.rollback()
        print e.message
        return 1
