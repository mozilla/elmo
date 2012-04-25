# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''View methods for the source/pushlog views.
'''

from itertools import cycle
from datetime import datetime
import operator
from time import mktime

from django.template.loader import render_to_string
from django.shortcuts import render
from django.db.models import Q, Max

from life.models import Push, Repository


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
    for p in paths:
        q = q.filter(changesets__files__path__contains=p)
    if paths:
        search['path'] = paths
    pushes = q.distinct().order_by('-push_date')[start:]
    if limit is not None:
        pushes = pushes[:(start + limit)]
    pushrows = [{'push': p,
                 'tip': p.changesets.order_by('-pk')[0],
                 'changesets': p.changesets.order_by('-pk')[1:],
                 'class': 'parity%d' % odd,
                 'span': p.changesets.count(),
                 }
                for p, odd in zip(pushes, cycle([1, 0]))]
    if pushrows:
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
