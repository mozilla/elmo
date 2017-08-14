# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for compare-locales output and statistics, in particular dashboards
and progress graphs.
'''
from __future__ import absolute_import, division

from collections import defaultdict
from datetime import datetime, timedelta
import calendar

from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.conf import settings
from django.template.loader import render_to_string
from django.http import (HttpResponse, Http404,
                         HttpResponsePermanentRedirect)
from django.db.models import Min, Max
from django.views.generic.base import TemplateView
import json
import elasticsearch

from l10nstats.models import Run
from life.models import Locale, Tree
import shipping.views


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
    url = reverse(shipping.views.dashboard)
    if request.META.get('QUERY_STRING'):
        url += '?' + request.META.get('QUERY_STRING')
    return HttpResponsePermanentRedirect(url)


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

    Implemented with a D3 plot.
    """
    tree = locale = None
    tree = get_object_or_404(Tree, code=request.GET.get('tree'))
    locale = get_object_or_404(Locale, code=request.GET.get('locale'))
    highlights = defaultdict(dict)
    for param in sorted(
            (p for p in request.GET.iterkeys() if p.startswith('hl-'))):
        try:
            _, i, kind = param.split('-')
            i = int(i)
        except:
            continue
        highlights[i][kind] = request.GET.get(param)
    for i, highlight in highlights.items():
        for k in ('s', 'e', 'c'):
            if k not in highlight:
                highlights.pop(i)
                break
    highlights = [v for i, v in sorted(highlights.iteritems())]
    q = q2 = Run.objects.filter(tree=tree, locale=locale)
    try:
        startrange = (q.order_by('srctime')
                      .exclude(srctime=None)
                      .values_list('srctime', flat=True)[0])
    except IndexError:
        # oops, we're obviously not building this, 404
        raise Http404("We're not building %s on %s" % (locale.code, tree.code))
    endrange = (datetime.utcnow()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=1))
    try:
        endtime = datetime.strptime(request.GET['endtime'], '%Y-%m-%d')
    except (KeyError, ValueError):
        # default to tomorrow
        endtime = endrange
    try:
        starttime = datetime.strptime(request.GET['starttime'], '%Y-%m-%d')
    except (KeyError, ValueError):
        starttime = endtime - timedelta(days=21)
    try:
        run = q2.filter(srctime__lt=starttime).order_by('-srctime')[0]
        runs = [{
            'srctime': starttime,
            'missing': run.allmissing + run.report,
            'obsolete': run.obsolete,
            'unchanged': run.unchanged,
            'run': run.id
            }]
    except IndexError:
        runs = []
    q2 = q2.filter(srctime__gte=starttime,
                   srctime__lte=endtime).order_by('srctime')
    runs += [
        {
            'srctime': r.srctime,
            'missing': r.allmissing + r.report,
            'obsolete': r.obsolete,
            'unchanged': r.unchanged,
            'run': r.id
        }
        for r in q2
    ] + [
        {
            'srctime': endtime,
            'missing': r.allmissing + r.report,
            'obsolete': r.obsolete,
            'unchanged': r.unchanged,
            'run': r.id
        }
    ]
    stamps = {}
    stamps['start'] = int(calendar.timegm(starttime.timetuple()))
    stamps['end'] = int(calendar.timegm(endtime.timetuple()))
    stamps['startrange'] = int(calendar.timegm(startrange.timetuple()))
    stamps['endrange'] = int(calendar.timegm(endrange.timetuple()))
    return render(request, 'l10nstats/history.html', {
                    'locale': locale.code,
                    'tree': tree.code,
                    'starttime': starttime,
                    'endtime': endtime,
                    'stamps': stamps,
                    'runs': runs,
                    'highlights': highlights
                  })


def tree_progress(request, tree):
    """Progress of all locales on a tree.

    Display the number of successful vs not locales.

    Implemented as d3.js plot.
    """
    tree = get_object_or_404(Tree, code=tree)

    locales = Locale.objects.filter(run__tree=tree, run__active__isnull=False)
    locales = list(locales)
    if not locales:
        return HttpResponse("no statistics for %s" % str(tree))
    q = Run.objects.filter(tree=tree)
    _d = q.aggregate(allStart=Min('srctime'), allEnd=Max('srctime'))
    allStart, allEnd = (_d[k] for k in ('allStart', 'allEnd'))

    startrange = allStart
    endrange = (datetime.utcnow()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=1))
    try:
        endtime = datetime.strptime(request.GET['endtime'], '%Y-%m-%d')
    except (KeyError, ValueError):
        # default to tomorrow
        endtime = endrange
    try:
        starttime = datetime.strptime(request.GET['starttime'], '%Y-%m-%d')
    except (KeyError, ValueError):
        starttime = endtime - timedelta(days=21)

    q = q.filter(locale__in=locales)
    q2 = q.filter(srctime__lte=endtime,
                  srctime__gte=starttime).order_by('srctime')
    q2 = q2.select_related('locale')

    initial_runs = getRunsBefore(tree, starttime,
                                 locales)
    datadict = defaultdict(dict)
    for loc, r in initial_runs.iteritems():
        stamp = int(calendar.timegm(starttime.timetuple()))
        datadict[stamp][loc] = (r.missing +
                                r.missingInFiles +
                                r.report)
    for r in q2:
        stamp = int(calendar.timegm(r.srctime.timetuple()))
        datadict[stamp][r.locale.code] = (r.missing +
                                          r.missingInFiles +
                                          r.report)
    data = [{'srctime': t, 'locales': json.dumps(datadict[t])}
            for t in sorted(datadict.keys())]

    try:
        bound = int(request.GET.get('bound', 0))
    except ValueError:
        bound = 0
    stamps = {}
    stamps['start'] = int(calendar.timegm(starttime.timetuple()))
    stamps['end'] = int(calendar.timegm(endtime.timetuple()))
    stamps['startrange'] = int(calendar.timegm(startrange.timetuple()))
    stamps['endrange'] = int(calendar.timegm(endrange.timetuple()))

    return render(request, 'l10nstats/tree_progress.html', {
                    'tree': tree.code,
                    'bound': bound,
                    'showBad': 'hideBad' not in request.GET,
                    'startTime': starttime,
                    'endTime': endtime,
                    'stamps': stamps,
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


class JSON2Adaptor(JSONAdaptor):
    def __init__(self, node, fragment='', base=''):
        self.fragment = fragment
        self.base = base
        self.node = node
        self.children = isinstance(self.node, dict)
        if not self.children:
            self.entities = []
            for data in self.node:
                if 'obsoleteFile' in data:
                    self.fileIs = 'obsolete'
                elif 'missingFile' in data:
                    self.fileIs = 'missing'
                elif 'missingEntity' in data:
                    self.entities.append({
                        'key': data['missingEntity'],
                        'class': 'missing'
                    })
                elif 'obsoleteEntity' in data:
                    self.entities.append({
                        'key': data['obsoleteEntity'],
                        'class': 'obsolete'
                    })
                else:
                    # warning or error, just one, but loop regardless
                    for cls, key in data.items():
                        self.entities.append({
                            'key': key,
                            'class': cls
                        })

    def __iter__(self):
        if self.children:
            if self.base:
                base = self.base + '/' + self.fragment
            else:
                base = self.fragment
            for fragment, node in sorted(self.node.items()):
                yield JSON2Adaptor(node, fragment, base)


class Counter:
    count = 0

    def increment(self):
        self.count += 1
        return str(self.count)


class CompareView(TemplateView):
    """HTML pretty-fied output of compare-locales.
    """
    template_name = 'l10nstats/compare.html'

    def get_context_data(self, **kwargs):
        context = super(CompareView, self).get_context_data(**kwargs)
        try:
            run = get_object_or_404(Run, id=self.request.GET.get('run'))
        except ValueError:
            raise Http404('Invalid ID')
        doc = self.get_doc(run)
        # JSON data from compare-locales changed with version 2.
        if doc and 'details' in doc:
            # First detect legacy format
            if isinstance(doc['details'].get('children'), list):
                nodes = list(
                    JSONAdaptor.adaptChildren(doc['details']['children']))
            else:
                # Format for compare-locales 2.0
                nodes = list(
                    JSON2Adaptor(doc['details']))
        else:
            nodes = None

        # create table widths for the progress bar
        widths = {}
        if run.total:
            for k in ('changed', 'missing', 'missingInFiles', 'report',
                      'unchanged'):
                widths[k] = getattr(run, k) * 300 // run.total
        context.update({
            'run': run,
            'nodes': nodes,
            'widths': widths,
            'counter': Counter(),
        })
        return context

    def get_doc(self, run):
        if not hasattr(settings, 'ES_COMPARE_HOST'):
            return None
        es = elasticsearch.Elasticsearch(hosts=[settings.ES_COMPARE_HOST])
        try:
            rv = es.get(index=settings.ES_COMPARE_INDEX,
                        doc_type='comparison',
                        id=run.id)
        except elasticsearch.TransportError:
            rv = {'found': False}
        if rv['found']:
            return rv['_source']
        return None
