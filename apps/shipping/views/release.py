# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import re
from collections import defaultdict
from datetime import datetime
from django.db.models import Q
from django.shortcuts import render, redirect
from django.views import generic

from shipping.models import Application, AppVersion, AppVersionTreeThrough


def select_appversions(request):
    avts = (AppVersionTreeThrough.objects
            .current()
            .filter(tree__code__endswith='central')
            .select_related('appversion__app'))
    apps = list(Application.objects.all())
    apps.sort(cmp=lambda r, l: cmp(len(r.code), len(l.code)))
    tree_kinds = set(code.split('_')[1]
                     for code in AppVersionTreeThrough.objects
                     .current()
                     .values_list('tree__code', flat=True))

    lastdigits = re.compile('\d+$')

    def inc(s):
        return lastdigits.sub(lambda m: str(int(m.group()) + 1), s)
    suggested = []
    for avt in avts:
        app = avt.appversion.app
        suggested.append({
            'name': str(app),
            'app': app.code,
            'nextversion': inc(avt.appversion.version),
            'nextcode': inc(avt.appversion.code)
            })
    migration_date = datetime.utcnow().replace(second=0,
                                               microsecond=0).isoformat()

    return render(request, 'shipping/release-migration.html', {
        'appvers': suggested,
        'tree_kinds': sorted(tree_kinds),
        'migration_date': migration_date,
        })


class MigrateAppversions(generic.View):
    '''Worker view for channel migration.
    The request part requires POST.
    '''
    def post(self, request):
        _redirect = redirect('select-dashboard')
        if not request.user.has_perm('shipping.can_ship'):
            return _redirect
        migration_date = datetime.strptime(request.POST.get('migration-date'),
                                           "%Y-%m-%dT%H:%M:%S")
        app_codes = request.POST.getlist('app')
        av_details = {}
        for app in app_codes:
            av_details[app] = {'code': request.POST[app + '-code'],
                               'version': request.POST[app + '-version'],
                               'fallback': app + '-fallback' in request.POST}
        app_ids = list(Application.objects
                       .filter(code__in=app_codes)
                       .values_list('id', flat=True))
        tree_kinds = request.POST.getlist('tree_kind')
        tree_q = Q()
        for tree_kind in tree_kinds:
            tree_q = tree_q | Q(tree__code__endswith='_%s' % tree_kind)
        self.migrateApps(migration_date, app_ids, tree_q, av_details)
        return _redirect

    def migrateApps(self, migration_date, app_ids, tree_q, av_details):
        branches4app = self.getBranchData(app_ids, tree_q)
        for app, branch in branches4app.iteritems():
            self.migrateBranch(migration_date, branch, av_details[app])

    def getBranchData(self, app_ids, tree_q):
        avts = (AppVersionTreeThrough.objects
                .current()
                .filter(appversion__app__in=app_ids)
                .filter(tree_q)
                .select_related('appversion__app', 'tree'))
        branches4app = defaultdict(dict)
        for avt in avts:
            branch = avt.tree.code.split('_')[1]
            branches4app[avt.appversion.app.code][branch] = avt
        return branches4app

    def migrateBranch(self, migration_date, branch_data, av_details):
        # hold old beta tree
        avt = branch_data['beta']
        avt.end = migration_date
        avt.save()
        # disabling sign-offs for release
        avt.appversion.accepts_signoffs = False
        avt.appversion.save()
        tree = avt.tree
        if 'aurora' in branch_data:
            # migrate aurora to beta
            avt = branch_data['aurora']
            avt.end = migration_date
            avt.save()
            (AppVersionTreeThrough.objects
             .create(appversion=avt.appversion,
                     tree=tree,  # tree is beta, see above
                     start=migration_date))
            avt.appversion.accepts_signoffs = True  # ensure signoffs are open
            avt.appversion.save()
            tree = avt.tree
        if 'central' in branch_data:
            # migrate central to vacant branch above, aurora or beta
            avt = branch_data['central']
            avt.end = migration_date
            avt.save()
            (AppVersionTreeThrough.objects
             .create(appversion=avt.appversion,
                     tree=tree,  # tree is aurora, see above
                     start=migration_date))
            avt.appversion.accepts_signoffs = True  # ensure signoffs are open
            avt.appversion.save()
            tree = avt.tree
            fallback = avt.appversion
            # create new appversion for central
            av = AppVersion(app=fallback.app,
                            version=av_details['version'],
                            code=av_details['code'],
                            fallback=None,
                            accepts_signoffs=True
                            )
            if av_details['fallback']:
                av.fallback = fallback
            av.save()
            (AppVersionTreeThrough.objects
             .create(appversion=av,
                     tree=tree,  # tree is central, see above
                     start=migration_date))
