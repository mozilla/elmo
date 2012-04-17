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

'''Views for compare-locales output and statistics, in particular dashboards
and progress graphs.
'''

from collections import defaultdict
from datetime import datetime, timedelta
import time

from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.http import (HttpResponse, HttpResponseNotFound,
                         HttpResponsePermanentRedirect,
                         HttpResponseBadRequest)
from django.db.models import Min, Max
from django.utils import simplejson

from l10nstats.models import Active, Run
from life.models import Locale, Tree
from tinder.views import generateLog


def getRunsBefore(tree, stamp, locales):
    """Get the latest run for each of the given locales and tree.

    Returns a dict of locale code and Run.
    """
    locales = list(locales)
    runs = {}
    while True:
        q = Run.objects.filter(tree=tree, locale__in=locales,
                               srctime__lt=stamp)
        q = q.order_by('-srctime')[:len(locales) * 2]
        q = q.select_related('locale')
        if q.count() == 0:
            return runs
        for r in q:
            if r.locale.code not in runs:
                runs[r.locale.code] = r
                locales.remove(r.locale)


def index(request):
    """redirect to the new improved dashboard which had all the features of the
    l10nstats dashboard.
    """
    url = reverse('shipping.views.dashboard')
    if request.META.get('QUERY_STRING'):
        url += '?' + request.META.get('QUERY_STRING')
    return HttpResponsePermanentRedirect(url)


def homesnippet():
    week_ago = datetime.utcnow() - timedelta(7)
    act = Active.objects.filter(run__srctime__gt=week_ago)
    act = act.order_by('run__tree__code')
    act = act.values_list('run__tree__code', flat=True).distinct()
    return render_to_string('l10nstats/snippet.html', {
            'trees': act,
            })


def teamsnippet(loc):
    act = Run.objects.filter(locale=loc, active__isnull=False)
    week_ago = datetime.utcnow() - timedelta(7)
    act = act.filter(srctime__gt=week_ago)
    act = act.order_by('tree__code').select_related('tree')
    return render_to_string('l10nstats/team-snippet.html', {
            'actives': act,
            })


def history_plot(request):
    """Progress of a single locale and tree.

    Implemented with a Simile Timeplot.
    """
    tree = locale = None
    endtime = datetime.utcnow().replace(microsecond=0)
    starttime = endtime - timedelta(14)
    second = timedelta(0, 1)
    if 'tree' in request.GET:
        try:
            tree = Tree.objects.get(code=request.GET['tree'])
        except Tree.DoesNotExist:
            pass
    if 'locale' in request.GET:
        try:
            locale = Locale.objects.get(code=request.GET['locale'])
        except Locale.DoesNotExist:
            pass
    if 'starttime' in request.GET:
        starttime = datetime.utcfromtimestamp(int(request.GET['starttime']))
    if 'endtime' in request.GET:
        endtime = datetime.utcfromtimestamp(int(request.GET['endtime']))
    if locale is not None and tree is not None:
        q = Run.objects.filter(tree=tree, locale=locale)
        q2 = q.filter(srctime__lte=endtime,
                      srctime__gte=starttime).order_by('srctime')
        p = None
        try:
            p = q2.filter(srctime__lt=starttime).order_by('-srctime')[0]
        except IndexError:
            pass

        def runs(_q, p):
            if p is not None:
                yield {'srctime': starttime,
                       'missing': p.missing + p.missingInFiles + p.report,
                       'obsolete': p.obsolete,
                       'unchanged': p.unchanged}
            r = None
            for r in _q:
                if p is not None:
                    yield {'srctime': r.srctime - second,
                           'missing': p.missing + p.missingInFiles + p.report,
                           'obsolete': p.obsolete,
                           'unchanged': p.unchanged}
                yield {'srctime': r.srctime,
                       'missing': r.missing + r.missingInFiles + r.report,
                       'obsolete': r.obsolete,
                       'unchanged': r.unchanged}
                p = r
            if r is not None:
                yield {'srctime': endtime,
                       'missing': r.missing + r.missingInFiles + r.report,
                       'obsolete': r.obsolete,
                       'unchanged': r.unchanged}
        stamps = {}
        stamps['start'] = int(time.mktime(starttime.timetuple()))
        stamps['end'] = int(time.mktime(endtime.timetuple()))
        stamps['previous'] = stamps['start'] * 2 - stamps['end']
        stamps['next'] = stamps['end'] * 2 - stamps['start']
        return render(request, 'l10nstats/history.html', {
                        'locale': locale.code,
                        'tree': tree.code,
                        'starttime': starttime,
                        'endtime': endtime,
                        'stamps': stamps,
                        'runs': runs(q2, p)
                      })
    return HttpResponseNotFound("sorry, gimme tree and locale")


def tree_progress(request, tree):
    """Progress of all locales on a tree.

    Display the number of successful vs not locales.

    Implemented as Simile Timeplot.
    """
    tree = get_object_or_404(Tree, code=tree)

    locales = Locale.objects.filter(run__tree=tree, run__active__isnull=False)
    locales = list(locales)
    if not locales:
        return HttpResponse("no statistics for %s" % str(tree))
    q = Run.objects.filter(tree=tree)
    _d = q.aggregate(allStart=Min('srctime'), allEnd=Max('srctime'))
    allStart, allEnd = (_d[k] for k in ('allStart', 'allEnd'))
    displayEnd = allEnd + timedelta(.5)

    endtime = datetime.utcnow().replace(microsecond=0)
    starttime = endtime - timedelta(14)

    if starttime > allEnd:
        # by default, we'd just see a flat graph, show half a day more
        # than allend
        endtime = displayEnd
        starttime = endtime - timedelta(14)

    if 'starttime' in request.GET:
        try:
            starttime = datetime.utcfromtimestamp(
              int(request.GET['starttime'])
            )
        except Exception:
            pass
        if starttime < allStart:
            # make sure that even though there nothing to see,
            # the slider shows all times
            allStart = starttime
    if 'endtime' in request.GET:
        try:
            endtime = datetime.utcfromtimestamp(int(request.GET['endtime']))
        except Exception:
            pass

    q = q.filter(locale__in=locales)
    q2 = q.filter(srctime__lte=endtime,
                  srctime__gte=starttime).order_by('srctime')
    q2 = q2.select_related('locale')

    initial_runs = getRunsBefore(tree, starttime,
                                 locales)
    datadict = defaultdict(dict)
    for loc, r in initial_runs.iteritems():
        datadict[starttime][loc] = (r.missing +
                                    r.missingInFiles +
                                    r.report)
    for r in q2:
        datadict[r.srctime][r.locale.code] = (r.missing +
                                              r.missingInFiles +
                                              r.report)
    data = [{'srctime': t, 'locales': simplejson.dumps(datadict[t])}
            for t in sorted(datadict.keys())]

    try:
        bound = int(request.GET.get('bound', 0))
    except ValueError:
        bound = 0

    return render(request, 'l10nstats/tree_progress.html', {
                    'tree': tree.code,
                    'bound': bound,
                    'showBad': 'hideBad' not in request.GET,
                    'startTime': starttime,
                    'endTime': endtime,
                    'explicitEnd': 'endtime' in request.GET,
                    'explicitStart': 'starttime' in request.GET,
                    'allStart': allStart,
                    'allEnd': displayEnd,
                    'data': data
                  })


class JSONAdaptor(object):
    """Helper class to make the json output from compare-locales
    easier to digest for the django templating language.
    """
    def __init__(self, node, base):
        self.fragment = node[0]
        self.base = base
        data = node[1]
        self.children = data.get('children', [])
        if 'value' in data:
            self.value = data['value']
            if 'obsoleteFile' in self.value:
                self.fileIs = 'obsolete'
            elif 'missingFile' in self.value:
                self.fileIs = 'missing'
            elif ('missingEntity' in self.value or
                  'obsoleteEntity' in self.value or
                  'warning' in self.value or
                  'error' in self.value):
                errors = [{'key': e, 'class': 'error'}
                          for e in self.value.get('error', [])]
                warnings = [{'key': e, 'class': 'warning'}
                          for e in self.value.get('warning', [])]
                entities = \
                    [{'key': e, 'class': 'missing'}
                     for e in self.value.get('missingEntity', [])] + \
                     [{'key': e, 'class': 'obsolete'}
                     for e in self.value.get('obsoleteEntity', [])]
                entities.sort(key=lambda d: d['key'])
                self.entities = errors + warnings + entities

    @classmethod
    def adaptChildren(cls, _lst, base=''):
        for node in _lst:
            yield JSONAdaptor(node, base)

    def __iter__(self):
        if self.base:
            base = self.base + '/' + self.fragment
        else:
            base = self.fragment
        return self.adaptChildren(self.children, base)

    @property
    def path(self):
        if self.base:
            return self.base + '/' + self.fragment
        return self.fragment


def compare(request):
    """HTML pretty-fied output of compare-locales.
    """
    try:
        run = get_object_or_404(Run, id=request.GET['run'])
    except ValueError:
        return HttpResponseBadRequest('Invalid ID')
    json = ''
    for step in run.build.steps.filter(name__startswith='moz_inspectlocales'):
        for log in step.logs.all():
            for chunk in generateLog(run.build.builder.master.name,
                                     log.filename):
                if chunk['channel'] == 5:
                    json += chunk['data']
    json = simplejson.loads(json)
    nodes = JSONAdaptor.adaptChildren(json['details'].get('children', []))
    summary = json['summary']
    if 'keys' not in summary:
        summary['keys'] = 0
    # create table widths for the progress bar
    widths = {}
    for k in ('changed', 'missing', 'missingInFiles', 'report', 'unchanged'):
        widths[k] = summary.get(k, 0) * 300 / summary['total']
    return render(request, 'l10nstats/compare.html', {
                    'run': run,
                    'nodes': nodes,
                    'widths': widths,
                    'summary': summary,
                  })
