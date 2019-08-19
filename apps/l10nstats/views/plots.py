# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for compare-locales output and statistics, in particular dashboards
and progress graphs.
'''
from __future__ import absolute_import, division
from __future__ import unicode_literals

from collections import defaultdict
from datetime import datetime, timedelta
import calendar

from django.shortcuts import render, get_object_or_404
from django.http import (HttpResponse, Http404)
from django.db.models import Min, Max
import json
import six

from l10nstats.models import Run
from life.models import Locale, Tree


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


def milestones(tree, starttime, endtime):
    return [
        {
            'timestamp': int(calendar.timegm(timestamp.timetuple())),
            'version': version,
        }
        for timestamp, version in
        tree.appvers_over_time
        .filter(end__isnull=False)
        .filter(end__gte=starttime, end__lte=endtime)
        .values_list('end', 'appversion__version')
    ]


def history_plot(request):
    """Progress of a single locale and tree.

    Implemented with a D3 plot.
    """
    tree = locale = None
    tree = get_object_or_404(Tree, code=request.GET.get('tree'))
    locale = get_object_or_404(Locale, code=request.GET.get('locale'))
    highlights = defaultdict(dict)
    for param in sorted(
            (p for p in six.iterkeys(request.GET) if p.startswith('hl-'))):
        try:
            _, i, kind = param.split('-')
            i = int(i)
        except ValueError:
            continue
        highlights[i][kind] = request.GET.get(param)
    for i, highlight in highlights.items():
        for k in ('s', 'e', 'c'):
            if k not in highlight:
                highlights.pop(i)
                break
    highlights = [v for i, v in sorted(six.iteritems(highlights))]
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
    ]
    if runs:
        r = runs[-1].copy()
        r['srctime'] = endtime
        runs.append(r)
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
                    'milestones': milestones(tree, starttime, endtime),
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
    for loc, r in six.iteritems(initial_runs):
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
                    'milestones': milestones(tree, starttime, endtime),
                    'data': data
                  })
