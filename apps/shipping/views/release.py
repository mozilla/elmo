import re
from collections import defaultdict
from datetime import datetime
from django.db.models import Max, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.views.decorators.http import require_POST

from shipping.models import (Application, AppVersion, AppVersionTreeThrough,
                             Milestone)


def select_appversions(request):
    avts = (AppVersionTreeThrough.objects
            .current()
            .filter(tree__code__endswith='central')
            .select_related('appversion__app'))
    apps = list(Application.objects.all())
    apps.sort(cmp=lambda r, l: cmp(len(r.code), len(l.code)))

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
        'migration_date': migration_date,
        })


class MigrateAppversions(generic.View):
    '''Worker view for channel migration.
    The request part requires POST.
    '''
    def post(self, request):
        _redirect = redirect('shipping.views.milestones')
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
        self.migrateApps(migration_date, app_ids, av_details)
        return _redirect

    def migrateApps(self, migration_date, app_ids, av_details):
        branches4app = self.getBranchData(app_ids)
        for app, branch in branches4app.iteritems():
            self.migrateBranch(migration_date, branch, av_details[app])

    def getBranchData(self, app_ids):
        avts = (AppVersionTreeThrough.objects
                .current()
                .filter(appversion__app__in=app_ids)
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
        # migrate central to aurora
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
                        accepts_signoffs=False
                        )
        if av_details['fallback']:
            av.fallback = fallback
        av.save()
        (AppVersionTreeThrough.objects
         .create(appversion=av,
                 tree=tree,  # tree is central, see above
                 start=migration_date))

migrate_appversions = MigrateAppversions.as_view()


def selectappversions4milestones(request):
    lastdigits = re.compile('\d+$')

    def inc(s):
        return lastdigits.sub(lambda m: str(int(m.group()) + 1), s)

    avts = list(AppVersionTreeThrough.objects
                .current()
                .filter(Q(tree__code__endswith='aurora') |
                        Q(tree__code__endswith='beta'))
                .select_related('appversion__app', 'tree'))
    appvers = [avt.appversion_id for avt in avts]
    latest_miles = list(AppVersion.objects
                        .filter(id__in=appvers)
                        .annotate(latest_mile=Max("milestone"))
                        .values_list('latest_mile', flat=True))
    miles = dict((ms.appver_id, {
        "code": inc(ms.code),
        "name": inc(ms.name),
        "good": ms.status == Milestone.SHIPPED
        })
        for ms in Milestone.objects.filter(id__in=latest_miles))
    data = defaultdict(dict)
    for avt in avts:
        branch = avt.tree.code.split("_")[1]
        data[avt.appversion.app][branch] = {
            "milestone": miles.get(avt.appversion_id,
                {
                    "code": avt.appversion.code + "_beta_b1",
                    "name": "Beta Build 1",
                    "good": True
                }),
            "appversion": avt.appversion,
            "branch": branch
        }
    data = sorted(({
        'app': app,
        'avs': [d['aurora'], d['beta']]
            } for app, d in data.iteritems()), key=lambda d: d['app'].code)
    return render(request, 'shipping/select-milestones.html', {
        "apps": data,
        })


@require_POST
def create_milestones(request):
    _redirect = redirect('shipping.views.milestones')
    if not request.user.has_perm('shipping.can_ship'):
        return _redirect
    new_miles = defaultdict(dict)
    for k, v in request.POST.iteritems():
        try:
            prop, av = k.split('-')
        except ValueError:
            # at least csrf is OK, so let's just pass all. get picky later.
            continue
        new_miles[av][prop] = v

    # first, let's make sure all data is OK, and then create stuff
    for av, details in new_miles.iteritems():
        details['av'] = get_object_or_404(AppVersion, code=av)
        if 'code' not in details:
            return HttpResponseBadRequest("'code' not in posted details")
        if 'name' not in details:
            return HttpResponseBadRequest("'name' not in posted details")

    # it survived the data input check,
    # now check those code not to already exist
    codes = [details['code'] for details in new_miles.itervalues()]
    already_exists = (Milestone.objects
                      .filter(code__in=codes)
                      .values_list('code', flat=True))
    if already_exists:
        return HttpResponseBadRequest(
            "Milestone for %s already created" % ', '.join(already_exists)
        )

    for details in new_miles.itervalues():
        details['av'].milestone_set.create(code=details['code'],
                                           name=details['name'],
                                           status=Milestone.OPEN)
    return _redirect
