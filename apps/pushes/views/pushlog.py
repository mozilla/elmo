# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''View methods for the source/pushlog views.
'''

from itertools import cycle
from datetime import datetime
import operator
from time import mktime

from django.shortcuts import render
from django.db.models import Q, Count

from life.models import Push, File


def pushlog(request, repo_name):
    '''View to show pushes and their changesets for:
    - all repositories starting with repo_name
    - or which names contain any of the `repo` query args
    - that don't contain any of the `exclude` query args in their name
    If file `path` parts are passed in, only show the changesets that
    affect the requested files.
    '''
    try:
        limit = int(request.GET['length'])
    except (ValueError, KeyError):
        limit = None
    startTime = endTime = None
    try:
        startTime = datetime.utcfromtimestamp(float(request.GET['from']))
    except (ValueError, KeyError):
        if limit is None:
            limit = 50
    try:
        endTime = datetime.utcfromtimestamp(float(request.GET['until']))
    except (ValueError, KeyError):
        pass
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
        q = q.filter(push_date__gte=startTime)
        search['from'] = startTime
    if endTime is not None:
        q = q.filter(push_date__lte=endTime)
        search['until'] = endTime
    if repo_name is not None:
        q = q.filter(repository__name__startswith=repo_name)
    elif repo_parts:
        repo_parts = map(lambda s: Q(repository__name__contains=s), repo_parts)
        if len(repo_parts) == 1:
            q = q.filter(repo_parts[0])
        else:
            q = q.filter(reduce(operator.or_, repo_parts))
        search['repo'] = repo_parts
    if excludes:
        q = q.exclude(repository__name__in=excludes)
    files = None
    if paths:
        pathquery = File.objects
        for p in paths:
            pathquery = pathquery.filter(path__contains=p)
        files = list(pathquery.values_list('id', flat=True))
        q = q.filter(changesets__files__in=files)
    if paths:
        search['path'] = paths
    pushes = q.distinct().order_by('-push_date')[start:]
    if limit is not None:
        pushes = pushes[:(start + limit)]
    # get all push IDs
    # the get the changesets for them
    push_ids = list(pushes.values_list('id', flat=True))
    push_changesets = (Push.changesets.through.objects
                       .filter(push__in=push_ids)
                       .order_by('-push__id', '-changeset__id'))
    pushcounts = {}
    if files:
        # we're only interested in the changesets that actually contain
        # our paths, reduce our query, and store how many changesets
        # there are per push without the filter
        push_changesets = push_changesets.filter(changeset__files__in=files)
        pushcounts.update(Push.objects
                          .filter(id__in=push_ids)
                          .annotate(changecount=Count('changesets'))
                          .values_list('id', 'changecount'))
    # get all pushes, with their changesets, possibly filtered
    pushrows = []
    push = None
    odd = 0
    for pc in push_changesets.select_related('push__repository', 'changeset'):
        if pc.push != push:
            if pushrows:
                pushrows[-1]['span'] = len(pushrows[-1]['changesets']) + 1
            push = pc.push
            odd = 1 - odd
            pushrows.append({
                'push': push,
                'tip': pc.changeset,
                'changesets': [],
                'class': 'parity%d' % odd,
                'change_count': pushcounts.get(push.id)
                })
        else:
            pushrows[-1]['changesets'].append(pc.changeset)
    if pushrows:
        # we have the last iteration to add still
        pushrows[-1]['span'] = len(pushrows[-1]['changesets']) + 1
        timespan = (int(mktime(pushrows[-1]['push'].push_date.timetuple())),
                    int(mktime(pushrows[0]['push'].push_date.timetuple())))
    else:
        timespan = None
    return render(request, 'pushes/pushlog.html', {
                    'pushes': pushrows,
                    'limit': limit,
                    'search': search,
                    'timespan': timespan,
                  })
