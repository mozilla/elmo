from collections import defaultdict
from datetime import datetime, timedelta

from django.shortcuts import render_to_response
from django.template import Context, loader
from django.http import HttpResponse, HttpResponseNotFound,\
    HttpResponseNotModified
from django.utils import simplejson

from l10nstats.models import *
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
    args = []
    if 'locale' in request.GET:
        locales = request.GET.getlist('locale')
        locales = Locale.objects.filter(code__in=locales)
        locales = locales.values_list('code', flat=True)
        if locales:
            args += ['locale=%s' % loc for loc in locales]
    if 'tree' in request.GET:
        trees = request.GET.getlist('tree')
        trees = Tree.objects.filter(code__in=trees)
        trees = trees.values_list('code', flat=True)
        if trees:
            args += ['tree=%s' % t for t in trees]
    return render_to_response('l10nstats/index.html',
                              {'args': args})

schema = {
    "types": {
        "Build": {
            "pluralLabel": "Builds"
            },
        "Priority": {
            "pluralLabel": "Priorities"
            }
        },
    "properties": {
        "changed": {
            "valueType": "number"
            },
        "missing": {
            "valueType": "number"
            },
        "starttime": {
            "valueType": "date"
            },
        "endtime": {
            "valueType": "date"
            }
        }
    }

def status_json(request):
    """The json output for the builds.
    
    Used by the main dashboard page Exhibit.
    """

    q = Run.objects.filter(active__isnull=False).order_by('tree__code',
                                                          'locale__code')
    if 'tree' in request.GET:
        q = q.filter(tree__code__in=request.GET.getlist('tree'))
    if 'locale' in request.GET:
        q = q.filter(locale__code__in=request.GET.getlist('locale'))
    leafs = ['tree__code', 'locale__code', 'id',
             'missing', 'missingInFiles',
             'errors', 'unchanged', 'total', 'obsolete', 'changed',
             'completion']
    def toExhibit(d):
        missing = d['missing'] + d['missingInFiles']
        result = 'success'
        tree = d['tree__code']
        locale = d['locale__code']
        if missing:
            result = 'failure'
        elif d['obsolete']:
            result = 'warnings'
        return {'id': '%s/%s' % (tree, locale),
                'runid': d['id'],
                'label': locale,
                'locale': locale,
                'tree': tree,
                'type': 'Build',
                'result': result,
                'missing': missing,
                'changed': d['changed'],
                'unchanged': d['unchanged'],
                'total': d['total'],
                'completion': d['completion']
                }
    items = map(toExhibit, q.values(*leafs))
    data = {'items': items}
    data.update(schema)
    return HttpResponse(simplejson.dumps(data, indent=2))


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

    if 'starttime' in request.GET:
        try:
            starttime = datetime.utcfromtimestamp(int(request.GET['starttime']))
        except Exception:
            pass
    if 'endtime' in request.GET:
        try:
            endtime = datetime.utcfromtimestamp(int(request.GET['endtime']))
        except Exception:
            pass

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


def grid(request):
    """View to show which runs are against which revisions.

    Parameters are locale and tree. If not given, shows a selection
    page.

    Experimental, might not stay.
    """
    trees = request.GET.getlist('tree')
    locales = request.GET.getlist('locale')
    if not (trees and locales):
        # hook up template here
        return HttpResponse("specify locale and tree")
    tree = trees[0]
    locale = locales[0]

    # find the runs for this locale and tree
    runs = Run.objects.filter(locale__code=locale,
                              tree__code=tree)[:20]
    changesets = Changeset.objects.filter(run__in=runs).distinct()
    changesets = changesets.order_by('push__push_date')
    changesets = changesets.select_related('push__repository')

    table = defaultdict(list)
    x = set()
    y = set()
    for run in runs:
        revs = run.revisions.all()
        l10n = None
        en = []
        for rev in revs:
            if rev.push.repository.forest_id is not None:
                l10n = rev
            else:
                en.append(rev)
        en.sort(key=lambda _rev: _rev.push.repository.name)
        en = tuple(en)
        x.add(l10n)
        y.add(en)
        table[(l10n,en)].append(run)
    X = sorted(x, key=lambda cs: cs.push.push_date)
    Y = sorted(y, key=lambda t: map(lambda cs: cs.push.push_date, t))
    rows = []
    for y in Y:
        row = [(x,y) in table and table[(x,y)] or None for x in X]
        rows.append(row)
    return render_to_response('l10nstats/grid.html',
                              {'X': X,
                               'rows': zip(Y, rows)})


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
                  'error' in self.value):
                errors = [{'key': e, 'class': 'error'}
                          for e in self.value.get('error', [])]
                entities = \
                    [{'key': e, 'class': 'missing'}
                     for e in self.value.get('missingEntity', [])] + \
                     [{'key': e, 'class': 'obsolete'}
                     for e in self.value.get('obsoleteEntity', [])]
                entities.sort(key=lambda d: d['key'])
                self.entities = errors + entities
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
    run = Run.objects.get(id=request.GET['run'])
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
    # create table widths for the progress bar
    _width = 300
    widths = {}
    for k in ('changed', 'missing', 'missingInFiles', 'unchanged'):
        widths[k] = summary[k]*300/summary['total']
    return render_to_response('l10nstats/compare.html',
                              {'run': run,
                               'nodes': nodes,
                               'widths': widths,
                               'summary': json['summary']})
