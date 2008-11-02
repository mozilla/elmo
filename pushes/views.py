import os.path

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404

from pushes.models import *
from django.conf import settings

from mercurial.hg import repository
from mercurial.ui import ui as _ui

def getHgDetails(repo_name, node, cache):
    try:
        repo = cache[repo_name]
    except KeyError:
        ui = _ui()
        repopath = os.path.join(settings.REPOSITORY_BASE,
                                repo_name, '')
        configpath = os.path.join(repopath, '.hg', 'hgrc')
        if not os.path.isfile(configpath):
            print "You need to clone " + repo_name
            return {'description': "MISSING"}
        ui.readconfig(configpath)
        repo = repository(ui, repopath)
        cache[repo_name] = repo

    try:
        ctx = repo.changectx(node)
    except Exception, e:
        print repo_name, e
        return {}
    return {'real_user': ctx.user(),
            'description': ctx.description()}

def default(request, repo_name):
    try:
        limit = int(request.GET['length'])
    except (ValueError, KeyError):
        limit = 10
    try:
        start = int(request.GET['start'])
    except (ValueError, KeyError):
        start = 0
    excludes = request.GET.getlist('exclude')
    paths = filter(None, request.GET.getlist('path'))
    q = Push.objects
    if repo_name is not None:
        q = q.filter(repository__name = repo_name)
    if excludes:
        q = q.exclude(repository__name__in = excludes)
    for p in paths:
        q = q.filter(changeset__files__path__contains=p)
    pushes = q.distinct().order_by('-push_date')[start:(start+limit-1)].values('user', 'pk', 'repository__name')
    repo_cache = {}
    odd = True
    push_ids = map(lambda p: int(p['pk']), pushes)
    changerevs = dict(Changeset.objects.filter(push__in=push_ids).order_by('pk').values_list('push','revision'))
    for p in pushes:
        d = getHgDetails(p['repository__name'], changerevs[p['pk']], repo_cache)
        p.update(d)
        p['class'] = 'parity%d' % odd
        odd = not odd
    t = loader.get_template('pushes/index.html')
    c = Context({
        'pushes': pushes
    })

    return HttpResponse(t.render(c))

def push_details(request, push):
    p = get_object_or_404(Push, pk=int(push))
    changes =  p.changeset_set.order_by('-pk').values_list('revision',
                                                           flat=True)
    t = loader.get_template('pushes/push-details.html')
    c = Context({
        'changes': changes,
        'baseurl': p.repository.url
    })

    return HttpResponse(t.render(c))
