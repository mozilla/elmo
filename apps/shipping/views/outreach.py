# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views to help with outreach around the rapid release cycle.
"""
from __future__ import absolute_import

from collections import defaultdict

from django.db.models import Q
from django.http import Http404
from django.shortcuts import render

from life.models import Forest
from shipping.models import Application, AppVersionTreeThrough
from shipping.api import flags4appversions
from l10nstats.models import Run
from functools import reduce


def select_apps(request):
    """Offer a selection of applications to reach out for.
    """
    # find all appversions that are working on the beta repos
    beta_forest = Forest.objects.get(name='releases/l10n/mozilla-beta')
    beta_avs = list(AppVersionTreeThrough.objects.current()
                    .filter(tree__in=beta_forest.tree_set.all())
                    .values_list('appversion', flat=True))
    beta_apps = (Application.objects
                 .filter(appversion__in=beta_avs)
                 .order_by('code'))
    return render(request, 'shipping/out-select-apps.html', {
                    'apps': beta_apps,
                  })


def data(request):
    app_codes = request.GET.getlist('app')
    if not app_codes:
        raise Http404('List of applications required')
    beta_apps = Application.objects.filter(code__in=app_codes)
    if len(app_codes) != beta_apps.count():
        raise Http404('Some of the given apps were not found')
    branches = request.GET.getlist('branch')

    f_aurora = Forest.objects.get(name='releases/l10n/mozilla-aurora')
    f_beta = Forest.objects.get(name='releases/l10n/mozilla-beta')
    forests = []
    if 'aurora' in branches:
        forests.append(f_aurora)
    if 'beta' in branches:
        forests.append(f_beta)
    name4app = dict(beta_apps.values_list('id', 'name'))
    # get AppVersion_Trees
    avts = (AppVersionTreeThrough.objects.current()
            .filter(appversion__app__in=name4app.keys(),
                    tree__l10n__in=forests)
            .order_by('appversion__code')
            .select_related('appversion__app', 'tree'))
    avts = list(avts)
    code4av = dict((avt.appversion_id, avt.appversion.code) for avt in avts)
    appname4av = dict((avt.appversion_id,
                       name4app[avt.appversion.app_id])
                      for avt in avts)
    tree4av = dict((avt.appversion_id, avt.tree_id) for avt in avts)
    av4tree = dict((avt.tree_id, avt.appversion_id) for avt in avts)
    locs = set()
    loc4tree = defaultdict(list)
    for t, l in (Run.objects
                 .filter(tree__in=tree4av.values(), active__isnull=False)
                 .values_list('tree', 'locale__code')
                 .distinct()):
        loc4tree[t].append(l)
        locs.add(l)
    locflags4av = flags4appversions([avt.appversion for avt in avts])
    loc4tree = defaultdict(list)
    for av, flags4loc in locflags4av.iteritems():
        if av.id not in tree4av:
            continue
        for loc, (real_av, flags) in flags4loc.iteritems():
            if real_av == av.code:
                continue
            loc4tree[tree4av[av.id]].append(loc)
    loc4tree = dict((t, locs) for t, locs in loc4tree.iteritems()
                    if locs)
    or_ = lambda l, r: l | r
    runqueries = reduce(or_,
                        (reduce(or_,
                                (Q(tree=t, locale__code=l) for l in locs))
                            for t, locs in loc4tree.iteritems()))
    actives = (Run.objects
               .filter(runqueries)
               .exclude(active__isnull=True)
               .select_related('locale'))
    missings = dict(((r.tree_id, r.locale.code), r.allmissing)
                    for r in actives)
    matrix = dict()
    columns = tuple(avt.appversion_id for avt in avts)
    for tree_id, locs in loc4tree.iteritems():
        av_id = av4tree[tree_id]
        for loc in locs:
            if loc not in matrix:
                matrix[loc] = [None] * len(avts)
            col_index = columns.index(av_id)
            entry = {'av': code4av[av_id],
                     'app': appname4av[av_id],
                     'missing': missings[(tree4av[av_id],
                                          loc)]}
            matrix[loc][col_index] = entry

    rows = [{'loc':loc, 'entries': matrix[loc]}
            for loc in sorted(matrix.keys())]

    return render(request, 'shipping/out-data.html', {
                    'apps': beta_apps,
                    'appvers': [avt.appversion for avt in avts],
                    'rows': rows,
                  })
