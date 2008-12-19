# Create your views here.
from django.shortcuts import render_to_response
from django.template import Context, loader
from django.http import HttpResponse, HttpResponseNotFound


import operator
from datetime import datetime, timedelta
from mbdb.models import *


resultclasses = ['success', 'warning', 'failure', 'skip', 'except']


class BColumn(object):
    '''Builder column

    Helper object to keep track of the parallel build columns per
    builder.

    '''

    def __init__(self, name):
        self.name = name
        self.cols = []

    def addRow(self):
        for c in self.cols:
            c[0]['rowspan'] += 1
        if not self.cols:
            self.cols.append([{'class': 'white',
                               'obj': None,
                               'rowspan': 1}])

    def changeCell(self, open_or_close, class_, obj):
        if open_or_close == 'open':
            cell = {'class': class_,
                    'obj': obj,
                    'rowspan': 1}
            if not self.cols:
                # we didn't even start yet, just add this as first inner col
                self.cols.append([cell])
                return
            # try to find a free column
            for i in xrange(len(self.cols)):
                if self.cols[i][0]['class'] == 'white':
                    # found the right column
                    break
            if i >= len(self.cols):
                # we don't have an free column, add a new one
                # first, fill it up with an empty cell
                oldrows = sum(map(lambda c: c['rowspan'], self.cols[0]))
                self.cols.append([{'class': 'white',
                               'obj': None,
                               'rowspan': oldrows}])
            # add cell, increase rowspan of all others
            for j in xrange(len(self.cols)):
                if j == i:
                    c = self.cols[j]
                    # if the first cell has no rowspan, just replace it
                    if c[0]['rowspan'] == 0:
                        c[0] = cell
                    else:
                        c.insert(0, cell)
                else:
                    self.cols[j][0]['rowspan'] += 1
        else:
            # open_or_close == 'close'
            cell = {'class': 'white',
                    'obj': None,
                    'rowspan': 0}
            for c in self.cols:
                if c[0]['obj'] == obj:
                    c.insert(0, cell)
                    return
            print 'there should be a cell to close here', self.name, str(obj)

    def finish(self):
        '''Finish this builder column.

        Pops leading empyt cells.

        '''
        for c in self.cols:
            if c[0]['rowspan'] == 0:
                c.pop(0)

    @property
    def width(self):
        return len(self.cols)

def _waterfall(request):
    '''Inner helper for waterfall display. This method is factored out
    of waterfall for testing purposes.

    '''
    end_t = max(Build.objects.order_by('-pk')[0].starttime,
                Change.objects.order_by('-pk')[0].when)
    start_t = end_t - timedelta(1)/2
    buildf = {}
    props = []
    if request is not None:
        if 'endtime' in request.GET:
            try:
                end_t = datetime.utcfromtimestamp(int(request.GET['endtime']))
            except Exception:
                pass
        if 'starttime' in request.GET:
            try:
                start_t = datetime.utcfromtimestamp(int(request.GET['starttime']))
            except Exception:
                pass
        if 'hours' in request.GET:
            try:
                start_t = end_t - timedelta(1)*12/int(request.GET['hours'])
            except Exception:
                pass
        timeopts = ['endtime', 'starttime', 'hours']
        builderopts = ['name', 'category']
        buildopts = ['slavename']
        for k, v in request.GET.items():
            if k in timeopts:
                continue
            if k in builderopts:
                buildf[str('builder__' + k)] = v
            elif k in buildopts:
                buildf[str(k)] = v
            else:
                props.append(Property.objects.filter(name=k).filter(value=v))
        
    q_buildsdone = Build.objects.filter(endtime__gt = start_t,
                                        starttime__lte = end_t)
    if buildf:
        q_buildsdone = q_buildsdone.filter(**buildf)
    for p in  props:
        q_buildsdone = q_buildsdone.filter(properties__in = p)
    print "found %d builds" % q_buildsdone.count()
    q_stepsrunning = Step.objects.filter(build__endtime__isnull = True,
                                         build__starttime__gt = start_t)
    if buildf:
        stepf = dict(('build__' + k, v) for k, v in buildf.iteritems())
        q_stepsrunning = q_stepsrunning.filter(**stepf)
    for p in props:
        q_stepsrunning = q_stepsrunning.filter(build__properties__in = p)
    q_changes = Change.objects.filter(when__gt = start_t,
                                      when__lte = end_t)
    events = reduce(operator.add, [[(b.starttime, 'b_start', b),
                                    (b.endtime, 'b_end', b)]
                                   for b in q_buildsdone], [])
    events += [(c.when, 'change', c) for c in q_changes]
    events += reduce(operator.add, [[(s.starttime, 's_start', s),
                                     (s.endtime is not None and s.endtime
                                      or datetime.max, 's.end', s)]
                                    for s in q_stepsrunning], [])
    events.sort(lambda l,r:cmp(l[0], r[0]))
    builders = sorted(set(q_buildsdone.values_list('builder__name',
                                                   flat=True).distinct()) |
                      set(q_stepsrunning.values_list('build__builder__name',
                                                     flat=True).distinct()))
    cols = dict((builder, BColumn(builder)) for builder in builders)
    blame = BColumn('blame')
    for time, type_, obj in events:
        if type_ == 'change':
            # ignore for now, blame column
            blame.changeCell('open', 'white', obj)
            for bcol in cols.itervalues():
                bcol.addRow()
        else:
            blame.addRow()
            if type_.startswith('b_'):
                # build
                class_ = 'build'
                if obj.result is not None:
                    class_ += ' ' + resultclasses[obj.result]
                builder = obj.builder.name
            else:
                class_ = 'step'
                if obj.result is not None:
                    class_ += ' ' + resultclasses[obj.result]
                builder = obj.build.builder.name
            if type_.endswith('end'):
                open_or_close = 'close'
            else:
                open_or_close = 'open'
            for bname, bcol in cols.iteritems():
                if bname == builder:
                    bcol.changeCell(open_or_close, class_, obj)
                else:
                    bcol.addRow()

    blame.finish()
    for bcol in cols.values():
        bcol.finish()

    return blame.cols[0], cols

def waterfall(request):
    '''Waterfall view

    Main worker is _waterfall, this one just forwards the results
    to the template.

    '''
    blame, buildercolumns = _waterfall(request)
    builders = sorted(buildercolumns.keys())
    head = [{'name': 'blame', 'span': 1}]
    head += [{'name': b, 'span': buildercolumns[b].width}
             for b in builders]
    rows = [[]]
    spans = []
    bmap = {}
    i = j = -1
    bl = blame.pop(0)
    rows[0].append(bl)
    blspan = bl['rowspan']
    for b in builders:
        i += 1
        for col in buildercolumns[b].cols:
            j += 1
            bmap[j] = i
            cel = col.pop(0)
            spans.append(cel['rowspan'])
            rows[0].append(cel)
    while any(spans) or blspan:
        i = j = -1
        row = []
        blspan -= 1
        if blspan <= 0:
            if blame:
                bl = blame.pop(0)
                row.append(bl)
                blspan = bl['rowspan']
            else:
                blspan = 0
        for b in builders:
            i += 1
            for col in buildercolumns[b].cols:
                j += 1
                spans[j] -= 1
                if spans[j] <= 0:
                    if col:
                        cel = col.pop(0)
                        row.append(cel)
                        spans[j] = cel['rowspan']
                    else:
                        spans[j] = 0
        rows.append(row)
    return render_to_response('tinder/waterfall.html', 
                              {'heads': head,
                               'rows': rows})

def builds_for_change(request):
    try:
        changenumber = int(request.GET['change'])
        change = Change.objects.get(number = changenumber)
    except (ValueError, KeyError):
        return HttpResponseNotFound("Given change does not exist")

    builds = change.builds.order_by('starttime')
    running = []
    done = []
    for b in builds:
        if b.endtime is not None:
            done.append({'build': b, 'class': resultclasses[b.result]})
    
    return render_to_response('tinder/builds_for.html',
                              {'done_builds': done,
                               'change': change})


def showbuild(request, buildername, buildnumber):
    try:
        builder = Builder.objects.get(name=buildername)
    except Builder.DoesNotExist:
        return HttpResponseNotFound("No such Builder")
    try:
        buildnumber = int(buildnumber)
        build = builder.builds.get(buildnumber=buildnumber)
    except (ValueError, Build.DoesNotExist):
        return HttpResonseNotFound("No such build")

    steps = build.steps.order_by('pk')
    props = build.propertiesAsList()

    return render_to_response('tinder/showbuild.html',
                              {'build': build,
                               'steps': steps,
                               'props': props})
