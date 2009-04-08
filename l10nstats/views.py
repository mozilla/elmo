from collections import defaultdict
from datetime import datetime, timedelta

from django.shortcuts import render_to_response
from django.template import Context, loader
from django.http import HttpResponse, HttpResponseNotFound

from l10nstats.models import *

def getRunsBefore(tree, stamp, locales):
    """Get the latest run for each of the given locales and tree.

    Returns a dict of locale code and Run.
    """
    locales = list(locales)
    runs = {}
    while True:
        q = Run.objects.filter(tree=tree, locale__in=locales,
                               srctime__lt=stamp)
        q = q.order_by('-srctime')[:len(locales)*2]
        if q.count() == 0:
            return runs
        for r in q:
            if r.locale.code not in runs:
                runs[r.locale.code] = r
                locales.remove(r.locale)


def index(request):
    """The main dashboard entry page.
    
    Implemented with a Simile Exhibit.
    """
    # verify args?
    return render_to_response('l10nstats/index.html',
                              {'args': request.GET})


def status_json(request):
    """The json output for the builds.
    
    Used by the main dashboard page Exhibit.
    """
    
    return HttpResponse('{}')


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
                       'missing': p.missing + p.missingInFiles,
                       'obsolete': p.obsolete,
                       'unchanged': p.unchanged}
            for r in _q:
                if p is not None:
                    yield {'srctime': r.srctime - second,
                           'missing': p.missing + p.missingInFiles,
                           'obsolete': p.obsolete,
                           'unchanged': p.unchanged}
                yield {'srctime': r.srctime,
                       'missing': r.missing + r.missingInFiles,
                       'obsolete': r.obsolete,
                       'unchanged': r.unchanged}
                p = r
            yield {'srctime': endtime,
                   'missing': r.missing + r.missingInFiles,
                   'obsolete': r.obsolete,
                   'unchanged': r.unchanged}
        return render_to_response('l10nstats/history.html',
                                  {'locale': locale.code,
                                   'tree': tree.code,
                                   'runs': runs(q2, p)})
    return HttpResponseNotFound("sorry, gimme tree and locale")

def tree_progress(request, tree):
    """Progress of all locales on a tree.
    
    Display the number of successful vs not locales.
    
    Implemented as Simile Timeplot.
    """
    try:
        tree = Tree.objects.get(code=tree)
    except Tree.DoesNotExist:
        return HttpResponseNotFound("sorry, gimme tree")

    endtime = datetime.utcnow().replace(microsecond=0)
    starttime = endtime - timedelta(14)

    q = Run.objects.filter(tree=tree)
    q2 = q.filter(srctime__lte=endtime,
                  srctime__gte=starttime).order_by('srctime')

    initial_runs = getRunsBefore(tree, starttime,
                                 Locale.objects.filter(run__in=q2).distinct())
    results = {}
    for loc, r in initial_runs.iteritems():
        results[loc] = (r.missing + r.missingInFiles) == 0
    all_good = sum(results.values())
    initial_data = {'srctime': starttime,
                    'good': all_good,
                    'bad': len(results) - all_good}
    events = defaultdict(list)
    def data(_q):
        for r in _q:
            good = (r.missing + r.missingInFiles) == 0
            if r.locale.code in results and results[r.locale.code] != good:
                events[r.srctime].append((r.locale.code, good))
            results[r.locale.code] = good
            all_good = sum(results.values())
            yield {'srctime': r.srctime,
                   'good': all_good,
                   'bad': len(results) - all_good}
    all_data = [initial_data] + list(data(q2))
    trail_data = dict(all_data[-1])
    trail_data['srctime'] = endtime
    all_data.append(trail_data)
    eventlist = []
    for t in sorted(events.keys()):
        eventlist.append({'srctime': t,
                          'locales': ', '.join([c for c, g in events[t]])})

    return render_to_response('l10nstats/tree_progress.html',
                              {'tree': tree.code,
                               'startTime': starttime,
                               'endTime': endtime,
                               'events': eventlist,
                               'data': all_data})


def exhibit_empty_iframe(request):
    """Exhibit and other Simile widgets load __history__.html into an
    iframe for back and forth, return an empty page for those.
    """
    return HttpResponse()
