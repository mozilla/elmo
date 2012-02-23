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

'''Views for managing sign-offs and shipping metrics.
'''

from collections import defaultdict
import re
import urllib

from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django import http
from life.models import Locale, Tree, Push, Changeset
from l10nstats.models import Run_Revisions
from shipping.models import Milestone, AppVersion, Action, Application
from shipping.api import (signoff_actions, flag_lists, accepted_signoffs,
                          signoff_summary)
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Max
from django.views.decorators.cache import cache_control
from django.utils import simplejson
from django.utils.http import urlencode
from django.utils.safestring import mark_safe


def index(request):
    locales = Locale.objects.all().order_by('code')
    avs = AppVersion.objects.all().order_by('code')

    for i in avs:
        statuses = (Milestone.objects
                    .filter(appver=i.id)
                    .values_list('status', flat=True)
                    .distinct())
        if 1 in statuses:
            i.status = 'open'
        elif 0 in statuses:
            i.status = 'upcoming'
        elif 2 in statuses:
            i.status = 'shipped'
        else:
            i.status = 'unknown'

    return render(request, 'shipping/index.html', {
                    'locales': locales,
                    'avs': avs,
                  })


def homesnippet():
    q = (AppVersion.objects
         .filter(milestone__status=1)
         .select_related('app'))
    q = q.order_by('app__name', '-version')
    return render_to_string('shipping/snippet.html', {
            'appvers': q,
            })


class Run(dict):
    def __getattr__(self, key):  # for dot notation
        return self[key]

    def __setattr__(self, key, value):  # for dot notation setters
        self[key] = value


def teamsnippet(loc):
    runs = list(loc.run_set.filter(active__isnull=False).select_related('tree')
                .order_by('tree__code'))

    # this locale isn't active in our trees yet
    if not runs:
        return ''

    _application_codes = [(x.code, x) for x in Application.objects.all()]
    # sort their keys so that the longest application codes come first
    # otherwise, suppose we had these keys:
    #   'fe', 'foo', 'fennec' then when matching against a tree code called
    #   'fennec_10x' then, it would "accidentally" match on 'fe' and not
    #   'fennec'.
    _application_codes.sort(lambda x, y: -cmp(len(x[0]), len(y[0])))

    # Create these two based on all appversions attached to a tree so that in
    # the big loop on runs we don't need to make excessive queries for
    # appversions and applications
    _trees_to_appversions = {}
    for appver in (AppVersion.objects
                   .exclude(tree__isnull=True)
                   .select_related('tree')):
        _trees_to_appversions[appver.tree] = appver

    def tree_to_application(tree):
        for key, app in _application_codes:
            if tree.code.startswith(key):
                return app

    def tree_to_appversion(tree):
        return _trees_to_appversions.get(tree)

    # find good revisions to sign-off, latest run needs to be green.
    # keep in sync with api.annotated_pushes
    suggested_runs = filter(lambda r: r.allmissing == 0 and r.errors == 0,
                            runs)
    suggested_rev = dict(Run_Revisions.objects
                         .filter(run__in=suggested_runs,
                                 changeset__repositories__locale=loc)
                         .values_list('run_id', 'changeset__revision'))

    applications = defaultdict(list)
    pushes = set()
    for run_ in runs:
        # copy the Run instance into a fancy dict but only copy those whose
        # key doesn't start with an underscore
        run = Run(dict((k, getattr(run_, k))
                       for k in run_.__dict__
                       if not k.startswith('_')))
        run.allmissing = run_.allmissing  # a @property of the Run model
        run.tree = run_.tree  # foreign key lookup
        application = tree_to_application(run_.tree)
        run.changed_ratio = run.completion
        run.unchanged_ratio = 100 * run.unchanged / run.total
        run.missing_ratio = 100 * run.allmissing / run.total
        # cheat a bit and make sure that the red stripe on the chart is at
        # least 1px wide
        if run.allmissing and run.missing_ratio == 0:
            run.missing_ratio = 1
            for ratio in (run.changed_ratio, run.unchanged_ratio):
                if ratio:
                    ratio -= 1
                    break

        appversion = tree_to_appversion(run.tree)
        # because Django templates (stupidly) swallows lookup errors we
        # have to apply the missing defaults too
        run.pending = run.rejected = run.accepted = \
                      run.suggested_shortrev = run.appversion = None
        if appversion:
            run.appversion = appversion
            actions = [action_id for action_id, flag
                       in signoff_actions(
                          appversions=[run.appversion],
                          locales=[loc.id])
                          ]
            actions = Action.objects.filter(id__in=actions) \
                                    .select_related('signoff__push')
            # get current status of signoffs
            # we really only need the shortrevs, we'll get those below
            run.pending, run.rejected, run.accepted, __ = \
              signoff_summary(actions)
            pushes.update((run.pending, run.rejected, run.accepted))

            # get the suggested signoff
            if run_.id in suggested_rev:
                run.suggested_shortrev = suggested_rev[run_.id][:12]

        applications[application].append(run)
    # get the tip shortrevs for all our pushes
    pushes = map(lambda p: p.id, filter(None, pushes))
    tip4push = dict(Push.objects
                    .annotate(tc=Max('changesets'))
                    .filter(id__in=pushes)
                    .values_list('id', 'tc'))
    rev4id = dict(Changeset.objects
                  .filter(id__in=tip4push.values())
                  .values_list('id', 'revision'))
    for runs in applications.itervalues():
        for run in runs:
            for k in ('pending', 'rejected', 'accepted'):
                if run[k] is not None:
                    run[k + '_rev'] = rev4id[tip4push[run[k].id]][:12]
    applications = ((k, v) for (k, v) in applications.items())

    return render_to_string('shipping/team-snippet.html',
                            {'locale': loc,
                             'applications': applications,
                            })


def dashboard(request):
    # legacy parameter. It's better to use the About milestone page for this.
    if 'ms' in request.GET:
        url = reverse('shipping.views.milestone.about',
                      args=[request.GET['ms']])
        return redirect(url)

    query = defaultdict(list)
    subtitles = []

    if request.GET.get('av'):
        appver = get_object_or_404(AppVersion, code=request.GET['av'])
        subtitles.append(str(appver))
        query['av'].append(appver.code)

    if request.GET.get('locale'):
        locales_list = request.GET.getlist('locale')
        locales = (Locale.objects.filter(code__in=locales_list)
                   .values_list('code', flat=True))
        if len(locales) != len(locales_list):
            raise http.Http404("Invalid list of locales")
        query['locale'].extend(locales)
        subtitles += list(locales)

    if request.GET.get('tree'):
        trees_list = request.GET.getlist('tree')
        trees = (Tree.objects.filter(code__in=trees_list)
                 .values_list('code', flat=True))
        if len(trees) != len(trees_list):
            raise http.Http404("Invalid list of trees")
        query['tree'].extend(trees)

    return render(request, 'shipping/dashboard.html', {
                    'subtitles': subtitles,
                    'webdashboard_url': settings.WEBDASHBOARD_URL,
                    'query': mark_safe(urlencode(query, True)),
                  })


def milestones(request):
    """Administrate milestones.

    Opens an exhibit that offers the actions below depending on
    milestone status and user permissions.
    """
    # we need to use {% url %} with an exhibit {{.foo}} as param,
    # fake { and } to be safe in urllib.quote, which is what reverse
    # calls down the line.
    if '{' not in urllib.always_safe:
        always_safe = urllib.always_safe
        urllib.always_safe = always_safe + '{}'
    else:
        always_safe = None
    # XXX this should have some sort of try:finally: to safely restore urllib
    r = render(request, 'shipping/milestones.html', {
                  'login_form_needs_reload': True,
                  'request': request,
                })
    if always_safe is not None:
        urllib.always_safe = always_safe
    return r


@cache_control(max_age=60)
def stones_data(request):
    """JSON data to be used by milestones
    """
    latest = defaultdict(int)
    items = []
    stones = Milestone.objects.order_by('-pk').select_related('appver__app')
    maxage = 5
    for stone in stones:
        age = latest[stone.appver.id]
        if age >= maxage:
            continue
        latest[stone.appver.id] += 1
        items.append({'label': str(stone),
                      'appver': str(stone.appver),
                      'status': stone.status,
                      'code': stone.code,
                      'age': age})

    return http.HttpResponse(simplejson.dumps({'items': items}, indent=2))


def open_mstone(request):
    """Open a milestone.

    Only available to POST, and requires signoff.can_open permissions.
    Redirects to milestones().
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        request.user.has_perm('shipping.can_open')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            mstone.status = 1
            # XXX create event
            mstone.save()
        except:
            pass
    return http.HttpResponseRedirect(reverse('shipping.views.milestones'))


def _propose_mstone(mstone):
    """Propose a new milestone based on an existing one.

    Tries to find the last integer in name and version, increment that
    and create a new milestone.
    """
    last_int = re.compile('(\d+)$')
    name_m = last_int.search(mstone.name)
    if name_m is None:
        return None
    code_m = last_int.search(mstone.code)
    if code_m is None:
        return None
    name_int = int(name_m.group())
    code_int = int(code_m.group())
    if name_int != code_int:
        return None
    new_rev = str(name_int + 1)
    return dict(code=last_int.sub(new_rev, mstone.code),
                name=last_int.sub(new_rev, mstone.name),
                appver=mstone.appver.code)


def confirm_ship_mstone(request):
    """Intermediate page when shipping a milestone.

    Gathers all data to verify when shipping.
    Ends up in ship_mstone if everything is fine.
    Redirects to milestones() in case of trouble.
    """
    if not request.GET.get('ms'):
        raise http.Http404("ms must be supplied")
    mstone = get_object_or_404(Milestone, code=request.GET['ms'])
    if mstone.status != Milestone.OPEN:
        return http.HttpResponseRedirect(reverse('shipping.views.milestones'))
    statuses = flag_lists(appversions={'id': mstone.appver_id})
    pending_locs = []
    good = 0
    for (tree, loc), flags in statuses.iteritems():
        if 0 in flags:
            # pending
            pending_locs.append(loc)
        if 1 in flags:
            # good
            good += 1
    pending_locs.sort()
    return render(request, 'shipping/confirm-ship.html', {
                  'mstone': mstone,
                  'pending_locs': pending_locs,
                  'good': good,
                  'login_form_needs_reload': True,
                  'request': request,
                  })


def ship_mstone(request):
    """The actual worker method to ship a milestone.

    Redirects to milestones().
    """
    if request.method != "POST":
        return http.HttpResponseNotAllowed(["POST"])
    if not request.user.has_perm('shipping.can_ship'):
        # XXX: personally I'd prefer if this was a raised 4xx error (peter)
        # then I can guarantee better test coverage
        return http.HttpResponseRedirect(reverse('shipping.views.milestones'))

    mstone = get_object_or_404(Milestone, code=request.POST['ms'])
    if mstone.status != Milestone.OPEN:
        return http.HttpResponseForbidden('Can only ship open milestones')
    cs = (accepted_signoffs(id=mstone.appver_id)
          .values_list('id', flat=True))
    mstone.signoffs.add(*list(cs))  # add them
    mstone.status = 2
    # XXX create event
    mstone.save()

    return http.HttpResponseRedirect(reverse('shipping.views.milestones'))


def confirm_drill_mstone(request):
    """Intermediate page when fire-drilling a milestone.

    Gathers all data to verify when shipping.
    Ends up in drill_mstone if everything is fine.
    Redirects to milestones() in case of trouble.
    """
    if not request.GET.get('ms'):
        raise http.Http404("ms must be supplied")
    if not request.user.has_perm('shipping.can_ship'):
        return http.HttpResponseRedirect(reverse('shipping.views.milestones'))
    mstone = get_object_or_404(Milestone, code=request.GET['ms'])
    if mstone.status != 1:
        return http.HttpResponseRedirect(reverse('shipping.views.milestones'))

    drill_base = (Milestone.objects
                  .filter(appver=mstone.appver, status=2)
                  .order_by('-pk')
                  .select_related())
    proposed = _propose_mstone(mstone)
    return render(request, 'shipping/confirm-drill.html', {
                    'mstone': mstone,
                    'older': drill_base[:3],
                    'proposed': proposed,
                    'login_form_needs_reload': True,
                    'request': request,
                  })


def drill_mstone(request):
    """The actual worker method to ship a milestone.

    Only avaible to POST.
    Redirects to milestones().
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        'base' in request.POST and
        request.user.has_perm('shipping.can_ship')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            base = Milestone.objects.get(code=request.POST['base'])
            so_ids = list(base.signoffs.values_list('id', flat=True))
            mstone.signoffs = so_ids  # add signoffs of base ms
            mstone.status = 2
            # XXX create event
            mstone.save()
        except Exception:
            # XXX should deal better with this error
            pass
    return redirect(reverse('shipping.views.milestones'))
