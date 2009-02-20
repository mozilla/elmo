from itertools import cycle
from datetime import datetime
import operator
import os.path
from time import mktime

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404
from django.db.models import Q

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

def pushlog(request, repo_name):
    try:
        limit = int(request.GET['length'])
    except (ValueError, KeyError):
        limit = None
    startTime = endTime = None
    try:
        startTime = datetime.utcfromtimestamp(float(request.GET['from']))
        endTime = datetime.utcfromtimestamp(float(request.GET['until']))
    except (ValueError, KeyError):
        if limit is None:
            limit = 50
    try:
        start = int(request.GET['start'])
    except (ValueError, KeyError):
        start = 0
    excludes = request.GET.getlist('exclude')
    paths = filter(None, request.GET.getlist('path'))
    repo_parts = filter(None, request.GET.getlist('repo'))
    search = {}
    q = Push.objects
    if startTime is not None:
        q = q.filter(push_date__gte = startTime)
        search['from'] = startTime
    if endTime is not None:
        q = q.filter(push_date__lte = endTime)
        search['until'] = endTime
    if repo_name is not None:
        q = q.filter(repository__name = repo_name)
    elif repo_parts:
        repo_parts = map(lambda s:Q(repository__name__contains = s), repo_parts)
        if len(repo_parts) == 1:
            q = q.filter(repo_parts[0])
        else:
            q = q.filter(reduce(operator.or_, repo_parts))
        search['repo'] = repo_parts
    if excludes:
        q = q.exclude(repository__name__in = excludes)
    for p in paths:
        q = q.filter(changeset__files__path__contains=p)
    if paths:
        search['path'] = paths
    pushes = q.distinct().order_by('-push_date')[start:]
    if limit is not None:
        pushes = pushes[:(start+limit-1)]
    pushrows = [{'push': p,
                 'tip': p.changeset_set.order_by('-pk')[0],
                 'changesets': p.changeset_set.order_by('-pk')[1:],
                 'class': 'parity%d' % odd,
                 'span': p.changeset_set.count(),
                 }
                for p, odd in zip(pushes, cycle([1,0]))]
    if pushrows:
        timespan = (int(mktime(pushrows[-1]['push'].push_date.timetuple())),
                    int(mktime(pushrows[0]['push'].push_date.timetuple())))
    else:
        timespan = None
    return render_to_response('pushes/pushlog.html',
                              {'pushes': pushrows,
                               'limit': limit,
                               'search': search,
                               'timespan': timespan})
