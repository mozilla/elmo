# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for managing sign-offs and shipping metrics.
'''

from collections import defaultdict
from datetime import datetime, timedelta
import re
import urllib

from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django import http
from life.models import Locale, Tree, Push, Changeset
from l10nstats.models import Run_Revisions, Run, ProgressPosition
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
    '''Dashboard to create dashboard links'''
    trees = set(
        Tree.objects
        .filter(run__active__isnull=False)
        .distinct()
    )
    avts = (
        AppVersion.trees.through.objects
        .current()
        .filter(tree__in=trees)
        .select_related('appversion__app', 'tree')
    )
    locales = Locale.objects.all().order_by('code')
    apps = defaultdict(list)
    for avt in avts:
        apps[avt.appversion.app].append(avt)
        trees.discard(avt.tree)
    for avtlist in apps.itervalues():
        avtlist.sort(key=lambda avt: avt.appversion.version)

    applist = sorted(
        ({'name': str(app), 'avts': vals}
         for app, vals in apps.iteritems()),
         key=lambda d: d['name']
    )

    selected_trees = request.GET.getlist('tree')
    selected_avs = request.GET.getlist('av')
    selected_locales = request.GET.getlist('locale')

    return render(request, 'shipping/index.html', {
                    'locales': locales,
                    'apps': applist,
                    'trees': trees,
                    'selected_trees': selected_trees,
                    'selected_avs': selected_avs,
                    'selected_locales': selected_locales
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
         .select_related('tree', 'locale')),
        key=lambda r: (r.tree.code,
                       '' if r.locale.code == loc.code else r.locale.code)
    )

    # this locale isn't active in our trees yet
    if not runs:
        return ''

    # Create these two based on all appversions attached to a tree so that in
    # the big loop on runs we don't need to make excessive queries for
    # appversions and applications
    _trees_to_appversions = {}
    appversion_has_pushes = {}
    for avt in (AppVersion.trees.through.objects
                .current()
                .select_related('appversion__app', 'tree__l10n')):
        _trees_to_appversions[avt.tree] = avt.appversion
        # find out if the appversion has activity (if open for sign-offs)
        if not avt.appversion.accepts_signoffs:
            continue
        pushes = Push.objects.filter(repository__forest=avt.tree.l10n)
        pushes = pushes.filter(repository__locale__in=locs)
        if avt.start:
            pushes = pushes.filter(push_date__gt=avt.start)
        if avt.end:
            pushes = pushes.filter(push_date__lt=avt.end)
        locales_with_runs = (Run.revisions.through.objects
            .filter(run__tree=avt.tree, changeset__pushes__in=pushes)
            .values_list('run__locale', flat=True))
        for locale_id in locales_with_runs:
            appversion_has_pushes[(avt.appversion, locale_id)] = True

    def tree_to_appversion(tree):
        return _trees_to_appversions.get(tree)

    def tree_to_application(tree):
        av = tree_to_appversion(tree)
        return av and av.app or None

    # offer all revisions to sign-off.
    # in api.annotated_pushes, we only highlight the latest run if it's green
    suggested_runs = runs

    suggested_rev = dict(Run_Revisions.objects
                         .filter(run__in=suggested_runs,
                                 changeset__repositories__locale__in=locs)
                         .values_list('run_id', 'changeset__revision'))

    progresses = dict(
        ((pp.tree.code, pp.locale.code), pp) for pp in (
            ProgressPosition.objects
            .filter(locale__in=locs)
            .select_related('tree', 'locale')
            )
        )
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
        run.prog_pos = progresses.get((run.tree.code, run.locale.code))

        appversion = tree_to_appversion(run.tree)
        # because Django templates (stupidly) swallows lookup errors we
        # have to apply the missing defaults too
        defaults = (
            "pending", "actions", "accepted", "suggested_shortrev",
            "is_active", "under_review", "suggest_glyph", "suggest_class",
            "fallback")
        for attr in defaults:
            setattr(run, attr, None)
        run.appversion = appversion
        if appversion and appversion.accepts_signoffs:
            run.is_active = \
                appversion_has_pushes.get((appversion, run.locale_id))
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
                interesting_flags = (Action.PENDING, Action.ACCEPTED,
                                     Action.REJECTED)
                actions = list(Action.objects
                    .filter(id__in=flags.values(),
                            flag__in=interesting_flags)
                    .select_related('signoff__push')
                    .order_by('when'))
                # only keep a rejected sign-off it's the last
                if (Action.REJECTED in flags and
                    actions[-1].flag != Action.REJECTED):
                    actions = filter(lambda a: a.flag != Action.REJECTED,
                                     actions)
                pushes.update(a.signoff.push for a in actions)
                objects = [RunElement(
                    dict((k, getattr(a, k))
                          for k in a.__dict__
                          if not k.startswith('_')))
                    for a in actions]
                for a, obj in zip(actions, objects):
                    obj.signoff = a.signoff
                    obj.push = a.signoff.push
                    obj.flag_name = a.get_flag_display()
                run.actions = objects
                if Action.ACCEPTED in flags:
                    run.accepted = [obj for obj in objects
                        if obj.flag == Action.ACCEPTED][0]
                    objects.remove(run.accepted)
            if appversion.code != real_av:
                run.fallback = real_av

            # get the suggested signoff. If there are existing actions
            # we'll unset it when we get the shortrevs for those below
            if run_.id in suggested_rev:
                run.suggested_shortrev = suggested_rev[run_.id][:12]
                if run.errors:
                    run.suggest_glyph = 'bolt'
                    run.suggest_class = 'error'
                elif run.allmissing:
                    run.suggest_glyph = 'graph'
                    run.suggest_class = 'warning'
                else:
                    run.suggest_glyph = 'badge'
                    run.suggest_class = 'success'

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
            actions = [run.accepted] if run.accepted else []
            if run.actions:
                actions += run.actions
            for action in actions:
                action.rev = rev4id[tip4push[action.push.id]][:12]
                # unset the suggestion if there's existing signoff action
                if action.rev == run.suggested_shortrev:
                    run.suggested_shortrev = None
                    # if we have a pending sign-off as the last thing,
                    # let's say so
                    if action.flag == Action.PENDING:
                        run.under_review = True
    applications = sorted(
        ((k, v) for (k, v) in applications.items()),
        key=lambda t: t[0] and t[0].name or None
    )
    other_team_locales = Locale.objects.filter(id__in=team_locales)

    progress_start = datetime.utcnow() - timedelta(days=settings.PROGRESS_DAYS)

    return render_to_string('shipping/team-snippet.html',
                            {'locale': loc,
                             'other_team_locales': other_team_locales,
                             'applications': applications,
                             'progress_start': progress_start,
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

    progress_start = datetime.utcnow() - timedelta(days=settings.PROGRESS_DAYS)
    try:
        cachebuster = (
            '?%d' % Run.objects.order_by('-pk').values_list('id', flat=True)[0]
            )
    except IndexError:
        cachebuster = ''

    return render(request, 'shipping/dashboard.html', {
                    'subtitles': subtitles,
                    'PROGRESS_IMG_SIZE': settings.PROGRESS_IMG_SIZE,
                    'PROGRESS_IMG_NAME': settings.PROGRESS_IMG_NAME,
                    'cachebuster': cachebuster,
                    'progress_start': progress_start,
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
