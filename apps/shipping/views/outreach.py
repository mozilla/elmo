# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views to help with outreach around the rapid release cycle.
"""

import datetime

from django.db.models import Q
from django.http import Http404
from django.shortcuts import render

from life.models import Locale, Forest
from shipping.models import Application, AppVersion, Signoff, Action
from shipping.api import signoff_actions
from l10nstats.models import Run


# dateformat shared to roundtrip the branch dates between select_apps and data
_dateformat = '%Y-%m-%d'
# magic date for the rapid release schedule
epoch = datetime.datetime(2011, 7, 5)


def select_apps(request):
    """Offer a selection of applications to reach out for.
    """
    # find all appversions that are working on the beta repos
    beta_forest = Forest.objects.get(name='releases/l10n/mozilla-beta')
    beta_apps = (Application.objects
                 .filter(appversion__tree__l10n=beta_forest)
                 .order_by('code'))
    n = datetime.datetime.utcnow()
    sixweeks = (n - epoch).days / (6 * 7)
    auroradate = epoch + sixweeks * datetime.timedelta(6 * 7)
    betadate = auroradate - datetime.timedelta(6 * 7)
    return render(request, 'shipping/out-select-apps.html', {
                    'apps': beta_apps,
                    'auroradate': auroradate.strftime(_dateformat),
                    'betadate': betadate.strftime(_dateformat),
                  })


def data(request):
    app_codes = request.GET.getlist('app')
    if not app_codes:
        raise Http404('List of applications required')
    beta_apps = Application.objects.filter(code__in=app_codes)
    if len(app_codes) != beta_apps.count():
        raise Http404('Some of the given apps were not found')
    try:
        auroradate = datetime.datetime.strptime(request.GET.get('auroradate'),
                                                _dateformat)
    except (ValueError, TypeError):
        raise Http404("missing auroradate, or doesn't match %s" % _dateformat)
    try:
        betadate = datetime.datetime.strptime(request.GET.get('betadate'),
                                              _dateformat)
    except (ValueError, TypeError):
        raise Http404("missing betadate, or doesn't match %s" % _dateformat)

    branches = request.GET.getlist('branch')

    f_aurora = Forest.objects.get(name='releases/l10n/mozilla-aurora')
    f_beta = Forest.objects.get(name='releases/l10n/mozilla-beta')
    forests = []
    if 'aurora' in branches:
        forests.append(f_aurora)
    if 'beta' in branches:
        forests.append(f_beta)
    appvers = (AppVersion.objects.
               filter(app__in=list(beta_apps.values_list('id', flat=True)),
                      tree__l10n__in=forests)
               .order_by('code')
               .select_related('app', 'tree'))
    appvers = list(appvers)
    beta_av = dict.fromkeys(av.id for av in appvers
                            if av.tree.l10n_id == f_beta.id)
    name4app = dict(beta_apps.values_list('id', 'name'))
    code4av = dict((av.id, av.code) for av in appvers)
    appname4av = dict((av.id, name4app[av.app_id]) for av in appvers)
    tree4av = dict((av.id, av.tree_id) for av in appvers)
    avq = {'id__in': [av.id for av in appvers]}
    actions = [action_id
               for action_id, flag in signoff_actions(appversions=avq)
               if flag == Action.ACCEPTED]
    old_signoffs = list(Signoff.objects
                       .filter(action__in=actions)
                       .exclude(push__push_date__gte=auroradate)
                       .select_related('push__repository'))
    # exclude signoffs on aurora pushes in the previous cycle
    # that are now on beta
    old_signoffs = filter(lambda so:
                          not (so.push.repository.forest == f_aurora and
                               so.appversion_id in beta_av and
                               so.push.push_date >= betadate and
                               so.push.push_date < auroradate),
                          old_signoffs)
    runqueries = (Q(locale=so.locale_id, tree=tree4av[so.appversion_id])
                  for so in old_signoffs)
    actives = (Run.objects
               .filter(reduce(lambda l, r: l | r, runqueries))
               .exclude(active__isnull=True))
    missings = dict(((r.tree_id, r.locale_id), r.allmissing)
                    for r in actives)
    matrix = dict()
    for signoff in old_signoffs:
        if signoff.locale_id not in matrix:
            matrix[signoff.locale_id] = [None] * len(appvers)
        for av_i, av in enumerate(appvers):
            if signoff.appversion_id == av.id:
                break
        entry = {'push': signoff.push.push_date,
                 'av': code4av[signoff.appversion_id],
                 'app': appname4av[signoff.appversion_id],
                 'missing': missings[(tree4av[signoff.appversion_id],
                                      signoff.locale_id)]}
        matrix[signoff.locale_id][av_i] = entry

    id4loc = dict((Locale.objects
                   .filter(id__in=matrix.keys())
                   .values_list('code', 'id')))
    rows = [{'loc':loc, 'entries': matrix[id4loc[loc]]}
            for loc in sorted(id4loc.keys())]

    return render(request, 'shipping/out-data.html', {
                    'apps': beta_apps,
                    'appvers': appvers,
                    'rows': rows,
                    'auroradate': auroradate.strftime(_dateformat),
                    'betadate': betadate.strftime(_dateformat),
                  })
