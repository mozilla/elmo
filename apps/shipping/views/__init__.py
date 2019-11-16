# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for managing sign-offs and shipping metrics.
'''
from __future__ import absolute_import, division
from __future__ import unicode_literals

from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta
import six
from six.moves import zip

from django.shortcuts import render
from django.views.generic import TemplateView
from django import http
from life.models import Locale, Tree, Push, Changeset
from l10nstats.models import Run
from shipping.models import AppVersion, Action
from shipping.api import flags4appversions
from django.conf import settings
from django.urls import reverse
from django.db.models import Max
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
    for avtlist in six.itervalues(apps):
        avtlist.sort(key=lambda avt: avt.appversion.version)

    applist = sorted(
        (
            {'name': str(app), 'avts': vals}
            for app, vals in six.iteritems(apps)
        ),
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


class Drivers(TemplateView):
    template_name = 'shipping/drivers.html'
    android_params = [
        '',
        'platforms=android',
        'multi_android-multilocale_repo=releases/mozilla-beta',
        'multi_android-multilocale_rev=default',
        'multi_android-multilocale_path=mobile/android/locales/maemo-locales'
    ]

    def get_context_data(self, **kwargs):
        context = super(Drivers, self).get_context_data(**kwargs)
        avts = (
            AppVersion.trees.through.objects
            .current()
            .filter(tree__run__active__isnull=False)
            .distinct()
            .order_by('appversion__app__name', 'appversion__code')
            .select_related('appversion__app', 'tree')
        )
        apps_and_versions = OrderedDict()
        for avt in avts:
            if avt.appversion.app not in apps_and_versions:
                apps_and_versions[avt.appversion.app] = []
            apps_and_versions[avt.appversion.app].append(avt)
            if avt.tree.code == 'fennec_beta':
                # ok, let's create the beta json url
                url = reverse('shipping-json_changesets')
                url += '?av=' + avt.appversion.code
                url += '&'.join(self.android_params)
                setattr(avt, 'json_changesets', url)
        context['apps_and_versions'] = apps_and_versions
        return context


class RunElement(dict):
    def __getattr__(self, key):  # for dot notation
        return self[key]

    def __setattr__(self, key, value):  # for dot notation setters
        self[key] = value


def teamsnippet(loc, team_locales):
    locs = Locale.objects.filter(pk__in=[loc.pk] + list(team_locales))
    runs = list(
        (Run.objects
         .filter(locale__in=locs, active__isnull=False)
         .select_related('tree', 'locale'))
    )

    # this locale isn't active in our trees yet
    if not runs:
        return {'template': 'shipping/team-snippet.html',
                'context': {'locale': loc,
                            'applications': [],
                            }}

    # Create these two based on all appversions attached to a tree so that in
    # the big loop on runs we don't need to make excessive queries for
    # appversions and applications
    appversion_has_pushes = {}
    _treeid_to_avt = {}
    for avt in (AppVersion.trees.through.objects
                .current()
                .filter(tree__in=set(run.tree.id for run in runs))
                .select_related('appversion__app', 'tree__l10n')):
        _treeid_to_avt[avt.tree.id] = avt

    runs_with_open_av = [
        run for run in runs
        if run.tree.id in _treeid_to_avt
        and _treeid_to_avt[run.tree.id].appversion.accepts_signoffs
    ]
    changesets = {
        tuple(t[:2]): t[2]
        for t in Run.revisions.through.objects
        .filter(run__in=runs_with_open_av,
                changeset__repositories__locale__in=locs)
        .values_list('run__tree', 'run__locale', 'changeset')
    }
    pushdates = {
        tuple(t[:2]): t[2]
        for t in Push.changesets.through.objects
        .filter(changeset__in=set(changesets.values()))
        .values_list(
            'changeset', 'push__repository__forest', 'push__push_date'
        )
    }
    for (treeid, locale_id), changeset in six.iteritems(changesets):
        avt = _treeid_to_avt[treeid]
        push_date = pushdates[(changeset, avt.tree.l10n.id)]
        if avt.start and push_date < avt.start:
            continue
        if avt.end and push_date > avt.end:
            continue
        appversion_has_pushes[(avt.appversion, locale_id)] = True

    def tree_to_appversion(tree):
        avt = tree.id in _treeid_to_avt and _treeid_to_avt[tree.id]
        return avt and avt.appversion or None

    def tree_to_version(tree):
        av = tree_to_appversion(tree)
        return av and av.version or None

    def tree_to_application(tree):
        av = tree_to_appversion(tree)
        return av and av.app or None

    runs.sort(
        key=lambda r: (tree_to_version(r.tree), r.tree.code,
                       '' if r.locale.code == loc.code else r.locale.code))

    # offer all revisions to sign-off.
    # in api.annotated_pushes, we only highlight the latest run if it's green
    suggested_runs = runs_with_open_av

    suggested_rev = dict(Run.revisions.through.objects
                         .filter(run__in=suggested_runs,
                                 changeset__repositories__locale__in=locs)
                         .values_list('run_id', 'changeset__revision'))

    applications = defaultdict(list)
    pushes = set()

    flags4av = flags4appversions(
        [_treeid_to_avt[run.tree.id].appversion for run in runs_with_open_av],
        locales=list(set(run.locale.id for run in runs_with_open_av)),
    )
    for run_ in runs:
        # copy the Run instance into a fancy dict but only copy those whose
        # key doesn't start with an underscore
        run = RunElement(
            {
                k: getattr(run_, k)
                for k in run_.__dict__
                if not k.startswith('_')
            }
        )
        run.locale = run_.locale
        run.allmissing = run_.allmissing  # a @property of the Run model
        run.tree = run_.tree  # foreign key lookup
        application = tree_to_application(run_.tree)
        run.changed_ratio = run.completion
        run.unchanged_ratio = 100 * run.unchanged // run.total
        run.missing_ratio = 100 * run.allmissing // run.total
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
        defaults = (
            "actions", "accepted", "suggested_shortrev",
            "is_active", "under_review", "suggest_glyph", "suggest_class",
            "fallback")
        for attr in defaults:
            setattr(run, attr, None)
        run.appversion = appversion
        run.is_active = \
            appversion_has_pushes.get((appversion, run.locale_id))
        applications[application].append(run)
        if appversion and appversion in flags4av:
            real_av, flags = (
                flags4av[appversion]
                .get(run_.locale.code, [None, {}])
            )

            # get current status of signoffs
            # we really only need the shortrevs, we'll get those below
            if flags:
                interesting_flags = (
                    Action.PENDING, Action.ACCEPTED, Action.REJECTED
                )
                actions = list(
                    Action.objects
                    .filter(id__in=flags.values(),
                            flag__in=interesting_flags)
                    .select_related('signoff__push')
                    .order_by('when', 'pk')
                )
                # only keep a rejected sign-off it's the last
                if (
                        Action.REJECTED in flags and
                        actions[-1].flag != Action.REJECTED
                ):
                    actions = [a for a in actions if a.flag != Action.REJECTED]
                pushes.update(a.signoff.push for a in actions)
                objects = [
                    RunElement(
                        {
                            k: getattr(a, k)
                            for k in a.__dict__
                            if not k.startswith('_')
                        }
                    )
                    for a in actions
                ]
                for a, obj in zip(actions, objects):
                    obj.signoff = a.signoff
                    obj.push = a.signoff.push
                    obj.flag_name = a.get_flag_display()
                run.actions = objects
                if Action.ACCEPTED in flags:
                    run.accepted = [
                        obj for obj in objects
                        if obj.flag == Action.ACCEPTED
                    ][0]
                    objects.remove(run.accepted)
            if appversion.code != real_av:
                run.fallback = real_av

            # get the suggested signoff. If there are existing actions
            # we'll unset it when we get the shortrevs for those below
            if run_.id in suggested_rev and run.is_active:
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

    # get the tip shortrevs for all our pushes
    pushes = [
        p.id
        for p in pushes
        if p is not None
    ]
    tip4push = dict(Push.objects
                    .annotate(tc=Max('changesets'))
                    .filter(id__in=pushes)
                    .values_list('id', 'tc'))
    rev4id = dict(Changeset.objects
                  .filter(id__in=tip4push.values())
                  .values_list('id', 'revision'))
    for runs in six.itervalues(applications):
        for run in runs:
            actions = [run.accepted] if run.accepted else []
            if run.actions:
                actions += run.actions
            for action in actions:
                action.rev = rev4id[tip4push[action.push.id]][:12]
                # unset the suggestion if there's existing signoff action
                if action.rev == run.suggested_shortrev:
                    run.suggested_shortrev = None
                    run.suggest_glyph = run.suggest_class = None
                    # if we have a pending sign-off as the last thing,
                    # let's say so
                    if action.flag == Action.PENDING:
                        run.under_review = True
    # Sort by appname, make trees without app come last via 'ZZZZZZ'
    applications = sorted(
        ((k, v) for (k, v) in applications.items()),
        key=lambda t: t[0] and t[0].name or 'ZZZZZZ'
    )
    other_team_locales = Locale.objects.filter(id__in=team_locales)

    progress_start = datetime.utcnow() - timedelta(days=settings.PROGRESS_DAYS)

    return {'template': 'shipping/team-snippet.html',
            'context': {'locale': loc,
                        'other_team_locales': other_team_locales,
                        'applications': applications,
                        'progress_start': progress_start,
                        }}


def dashboard(request):
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

    return render(request, 'shipping/dashboard.html', {
                    'subtitles': subtitles,
                    'progress_start': progress_start,
                    'query': mark_safe(urlencode(query, True)),
                  })
