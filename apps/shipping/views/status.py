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
#   Axel Hecht <l10n@mozilla.com>
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

'''Views for shipping metrics.
'''

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.generic import View
from life.models import Changeset
from l10nstats.models import Run
from shipping.api import accepted_signoffs, flag_lists
from shipping.models import (Milestone, Action,
                             Application, AppVersion)
from django.views.decorators.cache import cache_control
from django.utils import simplejson
from django.db.models import Max

from collections import defaultdict


class SignoffDataView(View):
    """Base view to reuse code to handle ms= or av= query params.

    First pass is process_request, which sets self.ms and self.av.
    Overload this method to handle further args.
    Second pass is get_data, which gets either
    - a shipped milestone, and calls data_for_milestone, or
    - a appversion query dict, and calls data_for_avq.
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
            avq = {"id": mile.appver_id}
        elif self.av is not None:
            appver = get_object_or_404(AppVersion, code=self.av)
            avq = {"id": appver.id}
        else:
            avq = {}
        return self.data_for_avq(avq)

    def data_for_avq(self, avq):
        return (accepted_signoffs(**avq),)

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


class Changesets(SignoffDataView):
    filename = 'l10n-changesets'

    def content(self, request, signoffs):
        sos = signoffs.annotate(tip=Max('push__changesets__id'))
        tips = dict(sos.values_list('locale__code', 'tip'))
        revs = Changeset.objects.filter(id__in=tips.values())
        revmap = dict(revs.values_list('id', 'revision'))
        return ('%s %s\n' % (l, revmap[tips[l]][:12])
                for l in sorted(tips.keys()))


l10n_changesets = cache_control(max_age=60)(Changesets.as_view())


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


shipped_locales = cache_control(max_age=60)(ShippedLocales.as_view())


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
            for appver in AppVersion.objects.filter(code__in=self.avs):
                if appver.tree and appver.tree.code not in self.trees:
                    self.trees.append(appver.tree.code)

        if self.trees:
            # make sure its appversion is in self.avs
            for appver in AppVersion.objects.filter(tree__code__in=self.trees):
                if appver.code not in self.avs:
                    self.avs.append(appver.code)

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
            for appver in (AppVersion.objects
                           .filter(tree__code__in=self.trees).values('id')):
                avq['id__in'].add(appver['id'])

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

        lsd = flag_lists(locales=lq, appversions=avq)
        tree_avs = appvers.exclude(tree__isnull=True)
        tree2av = dict(tree_avs.values_list("tree__code", "code"))
        tree2app = dict(tree_avs.values_list("tree__code", "app__code"))
        items = defaultdict(list)
        values = dict(Action._meta.get_field('flag').flatchoices)
        for k in lsd:
            # ignore tree/locale combos which have no active tree no more
            if k[0] is None:
                continue
            items[k] = [values[so] for so in lsd[k]]
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
                 for (tree, locale), values in sorted(items.iteritems(),
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


status_json = cache_control(max_age=60)(StatusJSON.as_view())
