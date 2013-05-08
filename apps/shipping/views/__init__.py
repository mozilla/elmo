# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for managing sign-offs and shipping metrics.
'''

from collections import defaultdict
import re
import urllib

from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django import http
from life.models import Locale, Tree, Push, Changeset
from l10nstats.models import Run_Revisions, Run
from shipping.models import Milestone, AppVersion, Action, Application
from shipping.api import flags4appversions, accepted_signoffs
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
        if Milestone.OPEN in statuses:
            i.status = 'open'
        elif Milestone.UPCOMING in statuses:
            i.status = 'upcoming'
        elif Milestone.SHIPPED in statuses:
            i.status = 'shipped'
        else:
            i.status = 'unknown'

    return render(request, 'shipping/index.html', {
                    'locales': locales,
                    'avs': avs,
                  })


def homesnippet():
    q = (AppVersion.objects
         .filter(milestone__status=Milestone.OPEN)
         .select_related('app'))
    q = q.order_by('app__name', '-version')
    return render_to_string('shipping/snippet.html', {
            'appvers': q,
            })


class RunElement(dict):
    def __getattr__(self, key):  # for dot notation
        return self[key]

    def __setattr__(self, key, value):  # for dot notation setters
        self[key] = value


def teamsnippet(loc, team_locales):
    locs = Locale.objects.filter(pk__in=[loc.pk] + list(team_locales))
    runs = sorted(
        (Run.objects
         .filter(locale__in=locs, active__isnull=False)
         .select_related('tree')),
        key=lambda r: (r.tree.code,
                       '' if r.locale.code == loc.code else r.locale.code)
    )

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
    for avt in (AppVersion.trees.through.objects
                .current()
                .select_related('appversion', 'tree')):
        _trees_to_appversions[avt.tree] = avt.appversion

    def tree_to_application(tree):
        for key, app in _application_codes:
            if tree.code.startswith(key):
                return app

    def tree_to_appversion(tree):
        return _trees_to_appversions.get(tree)

    # find good revisions to sign-off, latest run needs to be green.
    # keep in sync with api.annotated_pushes
    suggested_runs = filter(
        lambda r: r.allmissing == 0 and r.errors == 0,
        runs
    )

    suggested_rev = dict(Run_Revisions.objects
                         .filter(run__in=suggested_runs,
                                 changeset__repositories__locale__in=locs)
                         .values_list('run_id', 'changeset__revision'))

    applications = defaultdict(list)
    pushes = set()
    for run_ in runs:
        # copy the Run instance into a fancy dict but only copy those whose
        # key doesn't start with an underscore
        run = RunElement(dict((k, getattr(run_, k))
                       for k in run_.__dict__
                       if not k.startswith('_')))
        run.locale = run_.locale
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
                      run.suggested_shortrev = \
                      run.fallback = run.appversion = None
        if appversion and appversion.accepts_signoffs:
            run.appversion = appversion
            real_av, flags = (
                flags4appversions(
                    locales={'id': run_.locale.id},
                    appversions={'id': appversion.id}
                )
                .get(appversion, {})
                .get(run_.locale.code, [None, {}])
            )

            # get current status of signoffs
            # we really only need the shortrevs, we'll get those below
            if flags:
                actions = Action.objects.filter(id__in=flags.values()) \
                                        .select_related('signoff__push')
                action4id = dict((a.id, a)
                    for a in actions)
                for flag in (Action.PENDING, Action.ACCEPTED, Action.REJECTED):
                    if flag in flags:
                        a = action4id[flags[flag]]
                        setattr(run, a.get_flag_display(), a.signoff.push)
            if appversion.code != real_av:
                run.fallback = real_av
            pushes.update((run.pending, run.rejected, run.accepted))

            # get the suggested signoff. If there are existing actions
            # we'll unset it when we get the shortrevs for those below
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
                    # unset the suggestion if there's existing signoff action
                    if run[k + '_rev'] == run.suggested_shortrev:
                        run.suggested_shortrev = None
    applications = ((k, v) for (k, v) in applications.items())
    other_team_locales = Locale.objects.filter(id__in=team_locales)

    return render_to_string('shipping/team-snippet.html',
                            {'locale': loc,
                             'other_team_locales': other_team_locales,
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
        appvers_list = request.GET.getlist('av')
        appvers = (AppVersion.objects
                   .filter(code__in=appvers_list)
                   .select_related('app'))
        for av in appvers:
            query['av'].append(av.code)
            subtitles.append(str(av))
        if len(appvers_list) != len(query['av']):
            raise http.Http404("Invalid list of AppVersions")

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
                  'Milestone': Milestone,
                })
    if always_safe is not None:
        urllib.always_safe = always_safe
    return r


def stones_data(request):
    """JSON data to be used by milestones
    """
    latest = defaultdict(int)
    items = []
    stones = Milestone.objects.order_by('-pk').select_related('appver__app')
    building = list(AppVersion.trees.through.objects
                    .current()
                    .values_list('appversion', flat=True))
    maxage = 5
    for stone in stones:
        age = latest[stone.appver.id]
        if age >= maxage:
            continue
        latest[stone.appver.id] += 1
        items.append({'label': str(stone),
                      'appver': str(stone.appver),
                      'building': stone.appver_id in building,
                      'status': stone.status,
                      'code': stone.code,
                      'age': age})

    return http.HttpResponse(simplejson.dumps({'items': items}, indent=2))


def open_mstone(request):
    """Open a milestone.

    Only available to POST, and requires signoff.can_open permissions.
    Redirects to milestone.about().
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        request.user.has_perm('shipping.can_open')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            mstone.status = Milestone.OPEN
            # XXX create event
            mstone.save()
        except:
            pass
    return http.HttpResponseRedirect(reverse('shipping.views.milestone.about',
                                             args=[mstone.code]))


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
    flags4loc = (flags4appversions(appversions={'id': mstone.appver.id})
                 [mstone.appver])

    pending_locs = []
    good = 0
    for loc, (real_av, flags) in flags4loc.iteritems():
        if real_av == mstone.appver.code and Action.PENDING in flags:
            # pending
            pending_locs.append(loc)
        if Action.ACCEPTED in flags:
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

    Redirects to milestone.about().
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
    cs = (accepted_signoffs(mstone.appver)
          .values_list('id', flat=True))
    mstone.signoffs.add(*list(cs))  # add them
    mstone.status = Milestone.SHIPPED
    # XXX create event
    mstone.save()

    return http.HttpResponseRedirect(reverse('shipping.views.milestone.about',
                                             args=[mstone.code]))


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
    if mstone.status != Milestone.OPEN:
        return http.HttpResponseRedirect(reverse('shipping.views.milestones'))

    drill_base = (Milestone.objects
                  .filter(appver=mstone.appver, status=Milestone.SHIPPED)
                  .order_by('-pk')
                  .select_related())
    return render(request, 'shipping/confirm-drill.html', {
                    'mstone': mstone,
                    'older': drill_base[:3],
                    'login_form_needs_reload': True,
                    'request': request,
                  })


def drill_mstone(request):
    """The actual worker method to ship a milestone.

    Only avaible to POST.
    Redirects to milestone.about().
    """
    if request.method != "POST":
        return http.HttpResponseNotAllowed(["POST"])
    if not request.user.has_perm('shipping.can_ship'):
        # XXX: personally I'd prefer if this was a raised 4xx error (peter)
        # then I can guarantee better test coverage
        return http.HttpResponseRedirect(reverse('shipping.views.milestones'))

    mstone = get_object_or_404(Milestone, code=request.POST.get('ms'))
    base = get_object_or_404(Milestone, code=request.POST.get('base'))
    if mstone.status != Milestone.OPEN:
        return http.HttpResponseForbidden('Can only ship open milestones')

    so_ids = list(base.signoffs.values_list('id', flat=True))
    mstone.signoffs = so_ids  # add signoffs of base ms
    mstone.status = Milestone.SHIPPED
    # XXX create event
    mstone.save()
    return redirect(reverse('shipping.views.milestone.about',
                            args=[mstone.code]))
