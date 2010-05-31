# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''View methods for the source/pushlog views.
'''

from itertools import cycle
from datetime import datetime
import operator
import os.path
from time import mktime

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render_to_response, get_object_or_404
from django.db.models import Q, Max

from pushes.models import *
from django.conf import settings

from mercurial.hg import repository
from mercurial.ui import ui as _ui

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
        q = q.filter(repository__name__startswith = repo_name)
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
        q = q.filter(changesets__files__path__contains=p)
    if paths:
        search['path'] = paths
    pushes = q.distinct().order_by('-push_date')[start:]
    if limit is not None:
        pushes = pushes[:(start+limit)]
    pushrows = [{'push': p,
                 'tip': p.changesets.order_by('-pk')[0],
                 'changesets': p.changesets.order_by('-pk')[1:],
                 'class': 'parity%d' % odd,
                 'span': p.changesets.count(),
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

def homesnippet(request):
    repos = Repository.objects.filter(forest__isnull=False)
    repos = repos.annotate(lpd=Max('push__push_date'))
    repos = repos.order_by('-lpd')
    return render_to_string('pushes/snippet.html', {
            'repos': repos[:5],
            })
