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
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Axel Hecht <l10n@mozilla.com>
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

"""Views to help with outreach around the rapid release cycle.
"""

import datetime

from django.db.models import Q
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

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
    return render_to_response('shipping/out-select-apps.html',
                              {'apps': beta_apps,
                               'auroradate': auroradate.strftime(_dateformat),
                               'betadate': betadate.strftime(_dateformat),
                               },
                              context_instance=RequestContext(request))


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

    f_aurora = Forest.objects.get(name='releases/l10n/mozilla-aurora')
    f_beta = Forest.objects.get(name='releases/l10n/mozilla-beta')
    appvers = (AppVersion.objects.
               filter(app__in=list(beta_apps.values_list('id', flat=True)),
                      tree__l10n__in=[f_aurora, f_beta])
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

    return render_to_response('shipping/out-data.html',
                              {'apps': beta_apps,
                               'appvers': appvers,
                               'rows': rows,
                               'auroradate': auroradate.strftime(_dateformat),
                               'betadate': betadate.strftime(_dateformat),
                               },
                              context_instance=RequestContext(request))
