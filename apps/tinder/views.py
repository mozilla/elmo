# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views showing the build statuses.
'''
from __future__ import absolute_import, division, print_function

from django.db.models import Q
from django.db import connection
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseNotFound, Http404
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse


import operator
from bz2 import BZ2File
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
import calendar
from mbdb.models import (Build, Builder, BuildRequest,
                         Change, Change_Tags, Log, Master, NumberedChange,
                         SourceStamp, Step, Property)
from life.models import Push, Repository


resultclasses = ['success', 'warning', 'failure', 'skip', 'except']


class LogMountKeyError(Exception):
    pass


def debug_(*msg):
    if False:
        print(' '.join(msg))


def pmap(props, bld_ids):
    """Create a map of build ids to dicts with the requested properties.

    NOTE: this is a hack for optimization. Because there is no model for
    build properties we have to use the OneToOne table used to "connect" the
    Build and Property model in an efficient way which doens't cause massively
    complex joins which require temporary tables.

    NOTE 2: This function assumes that the list of `props` is reasonably
    limited or else the `WHERE id IN (...)` is going to in efficient.
    """
    if not bld_ids:
        return {}

    # model Build is "connected" to model Property with a OneToOne foreign key
    # reference which is not a model but is a database table.
    # We're accessing this auxilliary table to avoid complex joins which force
    # MySQL to use a temporary table.
    b2pf = Build._meta.get_field_by_name('properties')[0]
    args = {'t': b2pf.m2m_db_table(),
            'b': b2pf.m2m_column_name(),
            'p': b2pf.m2m_reverse_name()}
    pattern = '''SELECT `%(t)s`.`%(b)s`, `%(t)s`.`%(p)s`
      FROM `%(t)s` WHERE (
        `%(t)s`.`%(b)s` >= %(bs_min)s AND
        `%(t)s`.`%(b)s` <= %(bs_max)s AND
        `%(t)s`.`%(p)s` IN (%(ps)s));'''
    args['bs_min'] = min(bld_ids)
    args['bs_max'] = max(bld_ids)

    # create a set of primary keys of ALL properties by these names which we'll
    # use as a operator against the auxilliary table
    pq = Property.objects.filter(name__in=props)
    property_ids = set(pq.values_list('id', flat=True))
    args['ps'] = ','.join(map(str, property_ids))
    cursor = connection.cursor()
    cursor.execute(pattern % args)
    # master list of all properties (but not organized by build ids)
    props = defaultdict(list)
    # the subset of `property_ids` that is in the auxilliary table
    all_pids = set()
    for bid, pid in cursor.fetchall():
        props[bid].append(pid)
        all_pids.add(pid)
    prop_map = {}
    # build up a temporary dictionary of all properties to avoid multiple SQL
    # calls in the loop belowe
    for p in Property.objects.filter(id__in=all_pids):
        prop_map[p.id] = (p.name, p.value)
    rv = defaultdict(dict)
    for bid, pids in props.items():
        for p in pids:
            name, value = prop_map[p]
            rv[bid][name] = value
    return rv


def tbpl_inner(request):
    """Inner method used by both tbpl and tbpl_rows to do the actual work.
    The callers only differ in that tbpl generates the complete webpage
    including the reload logic, and tbpl_rows only returns the table rows,
    likely those that are newer than 'after' in request.GET.
    You can pass in a 'random' parameter to bypass caching.
    Pass in 'before' and you'll only get those sourcestamps with id matching
    or before the specified number.

    Any params other than 'after', 'before', and 'random' are taken to be
    querying build properties, where multiple properties of the same name are
    ORed together, and differently named properties restrict further.

    Example query would be
    tbpl_rows?after=54321&random=foo&locale=de&locale=pl&tree=fx35x
    which would get all fx35x builds for sourcestamps after 54321 for
    German and Polish.
    """
    ss = SourceStamp.objects.filter(builds__isnull=False).order_by('-pk')
    props = []
    if request is not None:
        for key, values in request.GET.iterlists():
            if key == "random":
                continue
            if key == "after":
                try:
                    id = values[-1]
                    ss = ss.filter(id__gt=int(id))
                except:
                    pass
                continue
            if key == "before":
                try:
                    id = values[-1]
                    ss = ss.filter(id__lte=int(id))
                except:
                    pass
                continue
            q = Q()
            for val in values:
                q = q | Q(name=key, value=val)
            if q:
                props.append(list(Property.objects
                                  .filter(q)
                                  .values_list('id', flat=True)))
    for _p in props:
        ss = ss.filter(builds__properties__in=_p)
    ss = ss.distinct()
    ss = list(ss[:10])
    blds = Build.objects.filter(sourcestamp__in=ss)
    for _p in props:
        blds = blds.filter(properties__in=_p)
    nc = NumberedChange.objects.filter(sourcestamp__in=ss)
    changetags = defaultdict(list)
    for ct in (Change_Tags.objects
               .filter(change__stamps__in=ss)
               .distinct()
               .select_related('tag')):
        changetags[ct.change_id].append(ct.tag.value)
    reponames = dict((id, '/'.join([b] + changetags[id]))
                     for id, b
                     in Change.objects
                         .filter(stamps__in=ss)
                         .distinct()
                         .values_list('id', 'branch'))
    repourls = dict(Repository.objects
                    .filter(name__in=set(reponames.values()))
                    .values_list('name', 'url'))

    def changer(c):
        reponame = '/'.join([c.branch] + changetags[c.id])
        try:
            rev = c.revision[:12]
            url = repourls[reponames[c.id]] + 'pushloghtml?changeset=' + rev
        except:
            url = 'about:blank'
            rev = 12 * '0'
        return {'id': c.id,
                'who': c.who,
                'url': url,
                'comments': c.comments,
                'when': c.when,
                'revision': rev,
                'repo': reponame}

    changes_for_source = defaultdict(list)
    for _nc in nc.select_related('change'):
        changes_for_source[_nc.sourcestamp_id].append(_nc.change)
    for _cs in changes_for_source.values():
        _cs.sort(key=lambda c: c.id, reverse=True)
    bld_ids = list(blds.values_list('id', flat=True))
    bprops = pmap(('locale', 'tree', 'slavename'), bld_ids)

    builds_for_source = defaultdict(list)
    for b in blds.filter(sourcestamp__in=ss).select_related('builder'):
        builds_for_source[b.sourcestamp_id].append(b)
    for _b in builds_for_source.values():
        _b.sort(key=lambda b: b.id)
    pending = defaultdict(int)
    for s in (BuildRequest.objects
               .filter(builds__isnull=True,
                       sourcestamp__in=ss)
               .values_list('sourcestamp', flat=True)):
        pending[s] += 1

    def chunks(ss):
        for s in ss:
            chunk = {}

            chunk['changes'] = map(changer, changes_for_source[s.id])
            chunk['builds'] = [{'id': b.id,
                                'result': b.result,
                                'props': bprops[b.id],
                                'start': b.starttime,
                                'end': b.endtime,
                                'number': b.buildnumber,
                                'builder': b.builder.name,
                                'build': b}
                               for b in builds_for_source[s.id]]
            chunk['id'] = s.id
            chunk['is_running'] = any(map(lambda c:
                                          c['end'] is None, chunk['builds']))
            chunk['pending'] = pending[s.id]
            yield chunk
    return chunks(ss)


def tbpl(request):
    return render(request, 'tinder/tbpl.html', {
                    'stamps': tbpl_inner(request),
                    'params': request.GET.iterlists(),
                  })


def tbpl_rows(request):
    qlen = len(connection.queries)
    r = render(request, 'tinder/tbpl-rows.html', {
                 'stamps': tbpl_inner(request)
               })
    # XXX: is this used at all?
    debug_(len(connection.queries) - qlen)
    return r


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
        debug_("%s received %s" % (self.name, open_or_close))
        if open_or_close == 'close':
            cell = {'class': class_,
                    'obj': obj,
                    'rowspan': 1}
            if not self.cols:
                # we didn't even start yet, just add this as first inner col
                self.cols.append([cell])
                return
            # try to find a free column
            hasEmptyCol = False
            for i in xrange(len(self.cols)):
                if self.cols[i][0]['class'] == 'white':
                    # found the right column
                    hasEmptyCol = True
                    break
            if not hasEmptyCol:
                # we don't have an free column, add a new one
                # first, fill it up with an empty cell
                oldrows = sum(map(lambda c: c['rowspan'], self.cols[0]))
                self.cols.append([{'class': 'white',
                               'obj': None,
                               'rowspan': oldrows}])
                i = len(self.cols) - 1
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
            # open_or_close == 'open'
            cell = {'class': 'white',
                    'obj': None,
                    'rowspan': 0}
            for c in self.cols:
                if c[0]['obj'] == obj:
                    c.insert(0, cell)
                    return
            debug_('there should be a cell to close here', self.name, str(obj))

    def finish(self):
        '''Finish this builder column.

        Pops leading empyt cells.

        '''
        for c in self.cols:
            if c[0]['rowspan'] == 0:
                c.pop(0)

    def rows(self):
        '''Iterator over all rows, returning a list of cells.'''

        # Can't hurt to finish ourselves
        self.finish()
        if not any(self.cols):
            # no content
            return
        spans = [0] * len(self.cols)
        while any(self.cols) or any(spans):
            r = []
            for i in xrange(len(self.cols)):
                if spans[i] == 0:
                    if self.cols[i]:
                        c = self.cols[i].pop()
                        spans[i] = c['rowspan'] - 1
                        if i == 0:
                            c['class'] += ' left'
                        if i == len(self.cols) - 1:
                            c['class'] += ' right'
                        r.append(c)
                else:
                    spans[i] -= 1
            yield r

    @property
    def width(self):
        return len(self.cols)

    def lengths(self):
        l = []
        for col in self.cols:
            ll = 0
            for cell in col:
                ll += cell['rowspan']
            l.append(ll)
        return l


def _waterfall(request):
    '''Inner helper for waterfall display. This method is factored out
    of waterfall for testing purposes.

    '''
    try:
        end_t = max(Build.objects.order_by('-pk')[0].starttime,
                    Change.objects.order_by('-pk')[0].when)
        start_t = end_t - timedelta(1) // 2
    except IndexError:
        # wallpaper against an empty build database
        end_t = datetime.max
        start_t = datetime.min
    buildf = {}
    props = []
    isEnd = True
    filters = None
    max_builds = None
    if request is not None:
        filters = request.GET.copy()
        if 'max-builds'in filters:
            try:
                max_builds = int(filters.pop('max-builds')[-1])
                if max_builds <= 0:
                    max_builds = None
            except:
                pass
        if 'endtime' in request.GET:
            try:
                end_t = datetime.utcfromtimestamp(int(request.GET['endtime']))
            except Exception:
                pass
            isEnd = False
        if 'starttime' in request.GET:
            try:
                start_t = datetime.utcfromtimestamp(
                              int(request.GET['starttime']))
            except Exception:
                pass
        if 'hours' in request.GET:
            try:
                td = timedelta(1) // 24 * int(request.GET['hours'])
                if 'starttime' in request.GET and 'endtime' not in request.GET:
                    end_t = start_t + td
                    isEnd = False
                else:
                    start_t = end_t - td
            except Exception:
                pass
        timeopts = ['endtime', 'starttime', 'hours']
        for opt in timeopts:
            if opt in filters:
                filters.pop(opt)
        builderopts = ['name', 'category']
        buildopts = ['slavename']
        for k, v in filters.items():
            if k in builderopts:
                buildf[str('builder__' + k)] = v
            elif k in buildopts:
                buildf[str(k)] = v
            else:
                props.append(Property.objects.filter(name=k).filter(value=v))

    # get the real hours, for consecutive queries
    time_d = end_t - start_t
    hours = int(round(time_d.seconds / 3600))
    if time_d.days:
        hours += time_d.days * 24

    q_buildsdone = Build.objects.filter(Q(endtime__gt=start_t) |
                                        Q(endtime__isnull=True),
                                        Q(starttime__lte=end_t))
    if buildf:
        q_buildsdone = q_buildsdone.filter(**buildf)
    for p in  props:
        q_buildsdone = q_buildsdone.filter(properties__in=p)
    debug_("found %d builds" % q_buildsdone.count())
    q_changes = Change.objects.filter(when__gt=start_t,
                                      when__lte=end_t)

    def ievents(builds, changes, max_builds=None):
        starts = []
        c_iter = changes.order_by('-when', '-pk').iterator()
        builds = builds.select_related('builder', 'slave', 'sourcestamp')
        try:
            c = c_iter.next()
        except StopIteration:
            c = None
        # yield an end change event if we have changes first
        if c:
            yield(None, 'end change', c)
        # yield end-events for running builds
        for b in (builds.filter(endtime__isnull=True)
                  .order_by('-starttime', '-pk')):
            starts.insert(0, b)
            yield (None, 'end started build', b)
            if max_builds:
                max_builds -= 1
        # restrict to only finished builds now
        builds = builds.filter(endtime__isnull=False)
        builds = builds.order_by('-endtime', '-pk')
        if max_builds:
            builds = builds[:max_builds]
        b_iter = builds.iterator()
        try:
            e = b_iter.next()
        except StopIteration:
            e = None
        b = None
        if starts:
            b = starts.pop()
        while e or b or c:
            if (e is not None and
                (b is None or e.endtime >= b.starttime) and
                (c is None or e.endtime >= c.when)):
                yield (e.endtime, 'end build', e)
                starts.insert(0, e)
                if b is not None:
                    starts.append(b)
                starts.sort(lambda r, l: cmp(r.starttime, l.starttime))
                b = starts.pop()
                try:
                    e = b_iter.next()
                except StopIteration:
                    e = None
                continue
            if (b is not None and
                (e is None or b.starttime > e.endtime) and
                (c is None or b.starttime > c.when)):
                yield (b.starttime, 'begin build', b)
                if starts:
                    b = starts.pop()
                else:
                    b = None
                continue
            assert c
            yield (c.when, 'start change', c)
            try:
                c = c_iter.next()
            except StopIteration:
                c = None
            if c:
                # we have more changes, open up the next cell
                yield(None, 'end change', c)

    builders = list(q_buildsdone
                    .values_list('builder__name',
                                 flat=True)
                    .distinct()
                    .order_by('builder__name'))
    cols = dict((builder, BColumn(builder)) for builder in builders)
    blame = BColumn('blame')
    for t, type_, obj in ievents(q_buildsdone, q_changes, max_builds):
        debug_(type_)
        if isinstance(obj, Build):
            debug_(str(obj.buildnumber))
        if type_.endswith('change'):
            if type_.startswith('end'):
                open_or_close = 'close'
            else:
                open_or_close = 'open'
            blame.changeCell(open_or_close, 'white', obj)
            if open_or_close == 'open':
                for bcol in cols.itervalues():
                    bcol.addRow()
        else:
            # build
            class_ = type_.split(' ', 1)[1]
            if obj.result is not None:
                class_ += ' ' + resultclasses[obj.result]
            builder = obj.builder.name
            if type_.startswith('end'):
                open_or_close = 'close'
            else:
                open_or_close = 'open'
            if open_or_close == 'close':
                blame.addRow()
            for bname, bcol in cols.iteritems():
                if bname == builder:
                    bcol.changeCell(open_or_close, class_, obj)
                elif open_or_close == 'close':
                    bcol.addRow()

    blame.finish()
    for bcol in cols.values():
        bcol.finish()

    if filters:
        filters = filters.urlencode() + '&'
    else:
        filters = ''

    def timestamp(dto):
        return "%d" % calendar.timegm(dto.utctimetuple())

    hourlist = [12, 24]
    if hours in hourlist:
        hourlist.remove(hours)
    hourlist.insert(0, hours)
    return blame, cols, filters, {'start': timestamp(start_t),
                                  'end': timestamp(end_t),
                                  'start_t': start_t,
                                  'end_t': end_t,
                                  'hourlist': hourlist,
                                  'hours': hours, 'isEnd': isEnd}


def waterfall(request):
    '''Waterfall view

    Main worker is _waterfall, this one just forwards the results
    to the template.

    '''
    blame, buildercolumns, filters, times = _waterfall(request)
    builders = [blame] + [buildercolumns[k]
                          for k in sorted(buildercolumns.keys())]
    head = [{'name': b.name, 'span': b.width}
            for b in builders]
    rows = []
    rows = [reduce(operator.add, t, [])
            for t in zip(*map(lambda b: b.rows(), builders))]
    return render(request, 'tinder/waterfall.html', {
                    'times': times, 'filters': filters,
                    'heads': head,
                    'rows': rows,
                  })


def builds_for_change(request):
    """View for builds for one particular change.

    Has a corresponding feed in BuildsForChangeFeed.
    """
    try:
        changenumber = int(request.GET['change'])
        change = Change.objects.get(number=changenumber)
    except (ValueError, KeyError):
        return HttpResponseNotFound("Given change does not exist")

    builds = (Build.objects
              .filter(sourcestamp__changes=change)
              .order_by('starttime'))
    pending = BuildRequest.objects.filter(builds__isnull=True,
                                          sourcestamp__changes=change).count()
    done = []
    for b in builds:
        done.append({
          'build': b,
          'class': (b.result is not None and resultclasses[b.result])
                     or ''})

    try:

        url = str(Push.objects
                 .get(changesets__revision__startswith=change.revision,
                      repository__name__startswith=change.branch))
    except:
        url = None

    return render(request, 'tinder/builds_for.html', {
                    'done_builds': done,
                    'pending': pending,
                    'url': url,
                    'change': change,
                  })


class BuildsForChangeFeed(Feed):
    ttl = str(5 * 60)
    title_template = 'tinder/builds_for_change_title.html'

    def get_object(self, request, id):
        """Return a closure to be used to create the feed for this change.

        404 for anything that isn't a single change ID.
        """
        self.request = request
        return Change.objects.get(number=id)

    def title(self, change):
        title = []
        pending = (BuildRequest.objects
                   .filter(builds__isnull=True,
                           sourcestamp__changes=change).count())
        if pending:
            title.append("%d pending" % pending)
        builds = Build.objects.filter(sourcestamp__changes=change)
        building = builds.filter(endtime__isnull=True).count()
        if building:
            title.append("%d building" % building)
        failed = builds.filter(result=2).count()
        if failed:
            title.append("%d failed" % failed)
        warnings = builds.filter(result=1).count()
        if warnings:
            title.append("%d warnings" % warnings)
        good = builds.filter(result=0).count()
        if good:
            title.append("%d good" % good)
        if not title:
            title.append("no builds")
        return ", ".join(title)

    def link(self, change):
        lnk = (reverse('tinder.views.builds_for_change') +
               '?change=%d' % change.pk)
        lnk = self.request.build_absolute_uri(lnk)
        return lnk

    def description(self, change):
        tmpl = '''Builds for %s by %s'''
        return tmpl % (change.comments, change.who)

    def items(self, change):
        builds = Build.objects.filter(sourcestamp__changes=change)
        return builds.order_by('starttime')

    def item_link(self, build):
        lnk = reverse('tinder_show_build',
                      args=(build.builder.name, build.buildnumber))
        lnk = self.request.build_absolute_uri(lnk)
        return lnk


def showbuild(request, buildername, buildnumber):
    try:
        builder = Builder.objects.get(name=buildername)
    except Builder.DoesNotExist:
        return HttpResponseNotFound("No such Builder")
    try:
        buildnumber = int(buildnumber)
        build = builder.builds.get(buildnumber=buildnumber)
    except (ValueError, Build.DoesNotExist):
        return HttpResponseNotFound("No such build")

    steps = build.steps.order_by('pk').select_related('log')
    props = build.propertiesAsList()
    return render(request, 'tinder/showbuild.html', {
                    'build': build,
                    'steps': steps,
                    'props': props,
                  })


class NoLogFile(Exception):
    '''Raised when the requested build log is not on disk'''
    pass


def generateLog(master, filename, channels):
    """Generic generator to read buildbot step logs.
    """
    if filename is None:
        # this sadly happens in some error conditions, we don't have a file
        raise NoLogFile("No filename given")
    try:
        base = settings.LOG_MOUNTS[master]
    except KeyError:
        raise LogMountKeyError(
            'The log mount %r is not in settings.LOG_MOUNTS'
            % master
        )
    head = re.compile('(\d+):(\d)')
    f = None
    filename = os.path.join(base, filename)
    try:
        f = BZ2File(filename + ".bz2", "r")
    except IOError:
        try:
            f = open(filename, "r")
        except IOError:
            raise NoLogFile("Log `%s` on master `%s` not found" %
                            (filename, master))

    def _iter(f):
        buflen = 64 * 1024
        buf = f.read(buflen)
        offset = 0
        while buf:
            m = head.match(buf, offset)
            if m:
                cnt = int(m.group(1))
                channel = int(m.group(2))
                offset = m.end()
                chunk = buf[offset:offset + cnt - 1]
                if len(chunk) < cnt - 1:
                    cnt -= len(chunk)
                    morebuf = f.read(cnt)
                    chunk += morebuf[:-1]  # drop ','
                    buf = []
                    offset = 0
                else:
                    offset += cnt
                if channels is None or channel in channels:
                    yield {'channel': channel, 'data': chunk}
            buf = buf[offset:] + f.read(buflen)
            offset = 0
    return _iter(f)


def showlog(request, step_id, name):
    """Show a log file.

    Right now, this only supports locally mounted buildbot logs.
    """
    def classify(chunks):
        classes = ["stdout", "stderr", "header"]
        for chunk in chunks:
            if chunk['channel'] < 3:
                yield {'class': classes[chunk['channel']],
                       'data': chunk['data']}
    step = get_object_or_404(Step, pk=step_id)
    log = get_object_or_404(step.logs, name=name)
    master = Master.objects.get(builders__builds__steps=step).name
    if log.filename is not None:
        try:
            chunks = generateLog(master, log.filename,
                                 channels=(Log.STDOUT, Log.STDERR, Log.HEADER))
        except NoLogFile, e:
            raise Http404(*e.args)
        return render(request, 'tinder/log.html', {
            'build': step.build,
            'file': log.filename,
            'chunks': classify(chunks),
            'isFinished': log.isFinished,
            })
    return render(request, 'tinder/html-log.html', {
        'build': step.build,
        'file': log.name,
        'content': log.html,
        })
