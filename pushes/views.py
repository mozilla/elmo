import os.path

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404

from dashboard.pushes.models import *
from dashboard import settings

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
    if repo_name is None:
        repos = Repository.objects
    else:
        repos = Repository.objects.filter(name = repo_name)
        if not repos:
            return HttpResponse("Can't find repository %s" % repo_name)
    repo_ids = repos.values_list('pk', flat=True)
    q = Push.objects.filter(repository__in=repos.all())
    if excludes:
        q = q.exclude(repository__name__in = excludes)
    for p in paths:
        q = q.filter(changeset__files__path__contains=p)
    pushes = q.distinct().order_by('-push_date')[start:(start+limit-1)].values('user', 'pk', 'repository__name')
    repo_cache = {}
    odd = True
    for p in pushes:
        cs = Changeset.objects.filter(push__pk = int(p['pk'])).order_by('-pk')[0]
        d = getHgDetails(p['repository__name'], cs.revision, repo_cache)
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
