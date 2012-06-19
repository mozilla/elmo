# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for shipping metrics.
'''
from collections import defaultdict

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.generic import View
from life.models import Changeset
from l10nstats.models import Run
from shipping.api import accepted_signoffs, flags4appversions
from shipping.models import (Milestone, Action,
                             Application, AppVersion)
from django.views.decorators.cache import cache_control
from django.utils import simplejson
from django.db.models import Max

from .utils import class_decorator


class SignoffDataView(View):
    """Base view to reuse code to handle ms= or av= query params.

    First pass is process_request, which sets self.ms and self.av.
    Overload this method to handle further args.
    Second pass is get_data, which gets either
    - a shipped milestone, and calls data_for_milestone, or
    - a appversion, and calls data_for_appversion.
    Both of these return tuples, which is then used by the
    actual content creation step, content(), which returns a string or
    iterator of strings, to be passed into the response.
    """
    filename = None

    def process_request(self, request, *args, **kwargs):
        self.ms = request.GET.get('ms')
        self.av = request.GET.get('av')

    def get_data(self):
        if self.ms is not None:
            mile = get_object_or_404(Milestone, code=self.ms)
            if mile.status == Milestone.SHIPPED:
                return self.data_for_milestone(mile)
            appver = mile.appver
        elif self.av is not None:
            appver = get_object_or_404(AppVersion, code=self.av)
        else:
            raise RuntimeError("Expecting either ms or av")
        return self.data_for_appversion(appver)

    def data_for_appversion(self, appver):
        return (accepted_signoffs(appver),)

    def data_for_milestone(self, mile):
        return (mile.signoffs,)

    def get(self, request, *args, **kwargs):
        self.process_request(request)
        data = self.get_data()
        content = self.content(request, *data)
        r = HttpResponse(content, content_type='text/plain; charset=utf-8')
        if self.filename:
            r['Content-Disposition'] = 'inline; filename="%s"' % self.filename
        return r


@class_decorator(cache_control(max_age=60))
class Changesets(SignoffDataView):
    filename = 'l10n-changesets'

    def content(self, request, signoffs):
        sos = signoffs.annotate(tip=Max('push__changesets__id'))
        tips = dict(sos.values_list('locale__code', 'tip'))
        revs = Changeset.objects.filter(id__in=tips.values())
        revmap = dict(revs.values_list('id', 'revision'))
        return ('%s %s\n' % (l, revmap[tips[l]][:12])
                for l in sorted(tips.keys()))

l10n_changesets = Changesets.as_view()


@class_decorator(cache_control(max_age=60))
class ShippedLocales(SignoffDataView):
    filename = 'shipped-locales'

    def content(self, request, signoffs):
        sos = signoffs.values_list('locale__code', flat=True)
        locales = list(sos) + ['en-US']

        def withPlatforms(loc):
            if loc == 'ja':
                return 'ja linux win32\n'
            if loc == 'ja-JP-mac':
                return 'ja-JP-mac osx\n'
            return loc + '\n'

        return map(withPlatforms, sorted(locales))


shipped_locales = ShippedLocales.as_view()


@class_decorator(cache_control(max_age=60))
class StatusJSON(SignoffDataView):

    EXHIBIT_SCHEMA = {
    "types": {
        "Build": {
            "pluralLabel": "Builds"
            },
        "Priority": {
            "pluralLabel": "Priorities"
            }
        },
    "properties": {
        "completion": {
            "valueType": "number"
            },
        "changed": {
            "valueType": "number"
            },
        "missing": {
            "valueType": "number"
            },
        "report": {
            "valueType": "number"
            },
        "warnings": {
            "valueType": "number"
            },
        "errors": {
            "valueType": "number"
            },
        "obsolete": {
            "valueType": "number"
            },
        "unchanged": {
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

    def process_request(self, request, *args, **kwargs):
        """Get hold of potential locale argument"""
        self.locales = request.GET.getlist('locale')
        self.trees = request.GET.getlist('tree')
        self.avs = request.GET.getlist('av')

        if self.avs:
            # make sure its tree is in self.trees
            trees = (AppVersion.trees.through.objects
                     .current()
                .filter(appversion__code__in=self.avs)
                .values_list('tree__code', flat=True))
            for tree in trees:
                if tree not in self.trees:
                    self.trees.append(tree)

        if self.trees:
            # make sure its appversion is in self.avs
            avs = (AppVersion.trees.through.objects
                   .current()
                .filter(tree__code__in=self.trees)
                .values_list('appversion__code', flat=True))
            for av in avs:
                if av not in self.avs:
                    self.avs.append(av)

    def get_data(self):
        runs = self.get_runs()
        signoffs = self.get_signoffs()
        return (runs + signoffs,)

    def get_runs(self):
        q = (Run.objects.filter(active__isnull=False)
                        .order_by('tree__code', 'locale__code'))
        if self.trees:
            q = q.filter(tree__code__in=self.trees)
        if self.locales:
            q = q.filter(locale__code__in=self.locales)
        leafs = ['tree__code', 'locale__code', 'id',
                 'missing', 'missingInFiles', 'report', 'warnings',
                 'errors', 'unchanged', 'total', 'obsolete', 'changed',
                 'completion']

        def toExhibit(d):
            missing = d['missing'] + d['missingInFiles']
            result = 'success'
            tree = d['tree__code']
            locale = d['locale__code']
            if missing or ('errors' in d and d['errors']):
                result = 'failure'
            elif d['obsolete']:
                result = 'warnings'

            rd = {'id': '%s/%s' % (tree, locale),
                  'runid': d['id'],
                  'label': locale,
                  'locale': locale,
                  'tree': tree,
                  'type': 'Build',
                  'result': result,
                  'missing': missing,
                  'report': d['report'],
                  'warnings': d['warnings'],
                  'changed': d['changed'],
                  'unchanged': d['unchanged'],
                  'total': d['total'],
                  'completion': d['completion']
                  }
            if 'errors' in d and d['errors']:
                rd['errors'] = d['errors']
            if 'obsolete' in d and d['obsolete']:
                rd['obsolete'] = d['obsolete']
            return rd
        return map(toExhibit, q.values(*leafs))

    def get_signoffs(self):
        avq = defaultdict(set)
        if self.avs:
            for appver in (AppVersion.objects
                           .filter(code__in=self.avs).values('id')):
                avq['id__in'].add(appver['id'])

        if self.trees:
            av_ids = (AppVersion.trees.through.objects
                      .current()
                .filter(tree__code__in=self.trees)
                .values_list('appversion_id', flat=True))
            avq['id__in'].update(av_ids)

        # restrict avq to building appversions open to signoffs
        currently_building = set(AppVersion.trees.through.objects
                                 .current()
                                 .filter(appversion__accepts_signoffs=True)
                                 .values_list('appversion_id', flat=True))
        if avq:
            avq['id__in'] &= currently_building
        else:
            avq['id__in'] = currently_building

        apps = list(AppVersion.objects
                    .filter(**avq)
                    .values_list('app', flat=True)
                    .distinct())
        if len(apps) == 1:
            given_app = Application.objects.get(id=apps[0]).code
        else:
            given_app = None
        if apps:
            appvers = AppVersion.objects.filter(app__in=apps)
        else:
            appvers = AppVersion.objects.all()
        lq = {}
        if self.locales:
            lq['code__in'] = self.locales

        locflags4av = flags4appversions(locales=lq, appversions=avq)
        tree_avs = (AppVersion.trees.through.objects
                    .current()
                    .filter(appversion__in=appvers))
        tree2av = dict(tree_avs.values_list("tree__code", "appversion__code"))
        av2tree = dict((av, tree) for tree, av in tree2av.iteritems())
        tree2app = dict(tree_avs.values_list("tree__code",
                                             "appversion__app__code"))
        values = dict(Action._meta.get_field('flag').flatchoices)
        so_items = {}
        for av in AppVersion.objects.filter(**avq):
            for loc, (real_av, flags) in locflags4av[av].iteritems():
                flag_values = [
                    (real_av == av.code or f != Action.ACCEPTED) and values[f]
                    or real_av
                    for f in flags]
                so_items[(av2tree[av.code], loc)] = flag_values
        # get shipped-in data, latest milestone of all appversions for now
        shipped_in = defaultdict(list)
        for _av in appvers.select_related('app'):
            for _ms in _av.milestone_set.filter(status=2).order_by('-pk')[:1]:
                break
            else:
                continue
            app = _av.app.code
            _sos = _ms.signoffs
            if self.locales:
                _sos = _sos.filter(locale__code__in=self.locales)
            for loc in _sos.values_list('locale__code', flat=True):
                shipped_in[(app, loc)].append(_av.code)

        # make a list now
        items = [{"type": "SignOff",
                  "label": "%s/%s" % (tree, locale),
                  "tree": tree,
                  "apploc": ("%s::%s" % (given_app or tree2app[tree],
                                         locale)),
                  "signoff": sorted(values)}
                 for (tree, locale), values in sorted(so_items.iteritems(),
                                                      key=lambda t:t[0])]
        items += [{"type": "Shippings",
                   "label": "%s::%s" % (av, locale),
                   "shipped": stones}
                  for (av, locale), stones in shipped_in.iteritems()]
        items += [{"type": "AppVer4Tree",
                   "label": tree,
                   "appversion": av}
                  for tree, av in tree2av.iteritems()]
        return items

    def content(self, request, items):
        data = self.EXHIBIT_SCHEMA.copy()
        data['items'] = items
        return simplejson.dumps(data, indent=2)


status_json = StatusJSON.as_view()
