# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views and helpers for sign-off views.
"""
from __future__ import absolute_import, print_function

import json
from collections import defaultdict

from django.db.models import Max, Q
from django.http import Http404, HttpResponseBadRequest, HttpResponse
from django.template import RequestContext
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
# TODO: from django.views.decorators.cache import cache_control
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from life.models import (
    Locale, Push, Repository, Push_Changesets, TeamLocaleThrough
)
from l10nstats.models import Run_Revisions, Run
from shipping.models import AppVersion, Signoff, Action
from shipping.api import flags4appversions
from shipping.forms import SignoffsPaginationForm


def signoff_locale(request, locale_code):
    get_object_or_404(Locale, code=locale_code)
    return redirect(reverse('homepage.views.locale_team', args=[locale_code]),
                    permanent=True)


class SignoffView(TemplateView):
    """View to show recent sign-offs and opportunities to sign off.

    This view is the main entry point to localizers to add sign-offs and to
    review what they're shipping.
    It's also the entry point for drivers to review existing sign-offs.
    """
    template_name = 'shipping/signoffs.html'

    count = 10

    attach_diffbases = True

    def get(self, request, locale_code, app_code):
        appver = get_object_or_404(AppVersion, code=app_code)
        lang = get_object_or_404(Locale, code=locale_code)
        context = self.get_context_data(lang, appver)
        return self.render_to_response(context)

    def get_context_data(self, lang, appver):
        # which pushes to show
        real_av, flags = (flags4appversions([appver],
            locales=[lang.id])
                          .get(appver, {})
                          .get(lang.code, [None, {}]))
        actions = list(Action.objects.filter(id__in=flags.values())
                       .select_related('signoff__push__repository', 'author'))

        # get current status of signoffs
        push4action = dict((a.id, a.signoff.push)
            for a in actions)
        pending = push4action.get(flags.get(Action.PENDING))
        rejected = push4action.get(flags.get(Action.REJECTED))
        accepted = push4action.get(flags.get(Action.ACCEPTED))

        if real_av != appver.code and accepted is not None:
            # we're falling back, add the accepted push to the table
            fallback = accepted
        else:
            fallback = None

        pushes_data = self.annotated_pushes(
            lang,
            appver,
            actions=actions,
            flags=flags,
            fallback=fallback,
            count=self.count,
        )

        # Check if this is the very first release.
        # Only applies to products that have a fallback (Firefox for example).
        first = appver.fallback is not None and accepted is None

        try:
            team_locale = (
                TeamLocaleThrough.objects.current().get(locale=lang).team
            )
        except TeamLocaleThrough.DoesNotExist:
            team_locale = lang

        if pushes_data['next_push_date']:
            next_push_date = pushes_data['next_push_date'].isoformat()
        else:
            next_push_date = None

        return {
            'appver': appver,
            'language': lang,
            'team_locale': team_locale,
            'pushes': pushes_data['pushes'],
            'pushes_left': pushes_data['pushes_left'],
            'next_push_date': next_push_date,
            'pending': pending,
            'rejected': rejected,
            'accepted': accepted,
            'first': first,
            'suggested_signoff': pushes_data['suggested_signoff'],
            'login_form_needs_reload': True,
            'fallback': fallback,
            'real_av': real_av,
        }

    def annotated_pushes(self,
                         lang, appver,
                         next_push_date=None,
                         actions=None, flags=None, fallback=None,
                         count=None):
        if count is None:
            count = self.count
        pushes_q = (Push.objects
                    .filter(changesets__branch__id=1)
                    .order_by('-push_date'))
        # Find the repos via trees_over_time
        forest4times = dict()
        tree4forest = dict()
        treename4forest = dict()
        for (_s, _e, _t, _tc, _f) in (appver.trees_over_time
                                 .values_list('start',
                                              'end',
                                              'tree',
                                              'tree__code',
                                              'tree__l10n')):
            forest4times[(_s, _e)] = _f
            tree4forest[_f] = _t
            treename4forest[_f] = _tc

        repo4forest = dict(Repository.objects
                           .filter(forest__in=forest4times.values(),
                                   locale=lang)
                           .values_list('forest', 'id'))
        repoquery = None
        for (_s, _e), _f in forest4times.iteritems():
            if _f not in repo4forest:
                # we don't have a repo for this locale in this forest
                # that's OK, continue
                continue
            qd = {'repository': repo4forest[_f]}
            if _s is not None:
                qd['push_date__gte'] = _s
            if _e is not None:
                qd['push_date__lte'] = _e
            if repoquery is not None:
                repoquery = repoquery | Q(**qd)
            else:
                repoquery = Q(**qd)
        pushes_q = pushes_q.filter(repoquery)

        # used when there is not a next_push_date
        initial_diff = []

        if next_push_date:
            # We're asked for pushes beyond the original cutoffs,
            # just use next_push_date and the limit.
            pushes_q = pushes_q.filter(
                push_date__lt=next_push_date
            ).distinct()
            pushes_left = pushes_q.distinct().count()
            pushes_q = pushes_q[:count]

        else:
            # This is the first load whereby we want to select all pushes up
            # to a certain cutoff.
            pushes_left = (pushes_q
                           .distinct()
                           .count())  # count pushes for this appversion
            cutoff_dates = []  # sign-off push dates, oldest is of interest
            action4id = dict((a.id, a) for a in actions)

            if Action.ACCEPTED in flags:
                a = action4id[flags[Action.ACCEPTED]]
                if not fallback:
                    cutoff_dates.append(a.signoff.push.push_date)
                initial_diff.append(a.signoff_id)

            if Action.PENDING in flags:
                a = action4id[flags[Action.PENDING]]
                cutoff_dates.append(a.signoff.push.push_date)
                initial_diff.append(a.signoff_id)

            if Action.REJECTED in flags:
                a = action4id[flags[Action.REJECTED]]
                cutoff_dates.append(a.signoff.push.push_date)
                # only add this signoff to initial_diff if we don't already
                # have an ACCEPTED and a PENDING signoff
                if len(initial_diff) < 2:
                    initial_diff.append(a.signoff_id)

            last_push_date = None
            if cutoff_dates:
                last_push_date = min(cutoff_dates)
                if fallback or Action.ACCEPTED not in flags:
                    try:
                        # go even further back in history then
                        last_push_date = list(
                            pushes_q
                            .filter(push_date__lt=last_push_date)
                            .values_list('push_date', flat=True)[:count]
                        )[-1]
                    except IndexError:
                        # ...but it's ok if there's nothing more, then
                        # we'll just keep the last_push_date from above
                        pass
                pushes_q = (
                    pushes_q
                    .filter(push_date__gte=last_push_date)
                ).distinct()
            else:
                # find the latest run, use at least that many
                # if they're less than count, use that
                avt = appver.trees_over_time.latest()
                runs = Run.objects.filter(
                    tree=avt.tree,
                    locale=lang)
                if avt.start:
                    runs = runs.filter(srctime__gt=avt.start)
                if avt.end:
                    # for historic views, also end time
                    runs = runs.filter(srctime__lt=avt.end)
                try:
                    cutoff = runs.order_by('-srctime')[0].srctime
                except IndexError:
                    cutoff = None
                if cutoff:
                    cutoff_q = pushes_q.filter(push_date__gte=cutoff).distinct()
                    if cutoff_q.count() > count:
                        pushes_q = cutoff_q
                    else:
                        pushes_q = pushes_q.distinct()[:count]
                else:
                    pushes_q = pushes_q.distinct()[:count]

        # get pushes, changesets and signoffs/actions
        _p = list(pushes_q.values_list('id', flat=True))
        pcs = (Push_Changesets.objects
               .filter(push__in=_p)
               .order_by('-push__push_date', '-changeset__id'))
        actions4push = defaultdict(list)
        handled_signoffs = set()
        for a in (Action.objects
                  .filter(signoff__push__in=_p,
                          signoff__appversion=appver)
                  .order_by('-when')
                  .select_related('signoff')):
            if a.signoff_id in handled_signoffs:
                continue
            handled_signoffs.add(a.signoff_id)
            actions4push[a.signoff.push_id].append(a)

        self.collect(pcs, actions4push)
        pushes = self.pushes

        # get latest runs for our changesets,
        # but restrict to the times that actually had the tree active
        cs4f = defaultdict(dict)
        for f, p, cs in pcs.values_list('push__repository__forest',
                                        'push',
                                        'changeset'):
            cs4f[f][cs] = p
        times4forest = dict((v, k) for k, v in forest4times.iteritems())
        run4push = dict()
        for f, changes in cs4f.iteritems():
            rrs = (Run_Revisions.objects
                   .order_by('changeset', 'run')
                   .filter(run__tree=tree4forest[f],
                           run__locale=lang,
                           changeset__in=changes.keys()))
            _s, _e = times4forest[f]
            if _s is not None:
                rrs = rrs.filter(run__srctime__gte=_s)
            if _e is not None:
                rrs = rrs.filter(run__srctime__lte=_e)
            for runrev in rrs.select_related('run'):
                run4push[changes[runrev.changeset_id]] = runrev.run

        # merge data back into pushes list
        suggested_signoff = None
        # initial_diff and runs
        if self.attach_diffbases and len(initial_diff) < 2 and pushes:
            pushes[0]['changes'][0].diffbases = (
              [None] * (2 - len(initial_diff))
            )

        # We did a count before, and then we did `pushes = pushes_q[:count]`
        # which will reduce the number ultimately left
        pushes_left -= len(pushes)

        # the oldest push_date of all these
        next_push_date = pushes[-1]['push_date'] if pushes else None

        for p in pushes:
            # initial_diff
            for sod in p['signoffs']:
                if sod['signoff'].id in initial_diff:
                    sod['diffbases'] = 1
            # runs
            if p['push_id'] in run4push:
                _r = run4push[p['push_id']]
                p['run'] = _r
                # should we suggest the latest run?
                # keep semantics of suggestion in sync with
                # shipping.views.teamsnippet
                if suggested_signoff is None:
                    if (not p['signoffs'] and
                        _r.allmissing == 0 and _r.errors == 0):
                        # source checks are good, suggest
                        suggested_signoff = p['id']
                    else:
                        # last push is signed off or red,
                        # don't suggest anything
                        suggested_signoff = False

        # mark up pushes that change forests/trees
        for i in xrange(len(pushes) - 1, 0, -1):
            if pushes[i]['forest'] != pushes[i - 1]['forest']:
                pushes[i]['new_forest'] = True

        return {
            'pushes': pushes,
            'suggested_signoff': suggested_signoff,
            'pushes_left': pushes_left,
            'next_push_date': next_push_date,
        }

    def collect(self, pcs, actions4push):
        """Prepare for collecting pushes. Result is set in self.pushes.

        pcs is a Push_Changesets queryset, ordered by -push_date, -changeset_id
        actions4push is a dict mapping push ids to lists of action objects

        The result is a list of dictionaries, describing the table rows to be
        shown for each push, as well as the detail information within.
        """
        self.actions4push = actions4push
        self.pushes = []
        self._prev = None
        self.rowcount = 0
        for _pc in pcs.select_related('push__repository', 'changeset'):
            push = _pc.push
            cs = _pc.changeset
            if self._prev != push.id:
                self.wrapup(push, cs)
            self.rowcount += 1
            self.pushes[-1]['changes'].append(cs)
        self.wrapup()

    def wrapup(self, push=None, cs=None):
        """Actual worker"""
        if self._prev is not None:
            self.pushes[-1]['changerows'] = self.rowcount
            signoffs = []
            for action in self.actions4push[self._prev]:
                _d = {'signoff': action.signoff, 'action': action}
                for snap in action.signoff.snapshot_set.all():
                    _i = snap.instance()
                    _n = _i._meta.object_name.lower()
                    _d[_n] = _i
                signoffs.append(_d)
            self.pushes[-1]['signoffs'] = signoffs
            self.pushes[-1]['rows'] = self.rowcount + len(signoffs)
        if push is not None:
            self.pushes.append({'changes': [],
                                'push_id': push.id,
                                'push_date': push.push_date,
                                'who': push.user,
                                'when': push.push_date,
                                'repo': push.repository.name,
                                'url': push.repository.url,
                                'forest': push.repository.forest_id,
                                'id': cs.shortrev})
            self.rowcount = 0
            self._prev = push.id


signoff = SignoffView.as_view()


class SignoffRowsView(SignoffView):

    template_name = 'shipping/signoff-rows.html'

    attach_diffbases = False

    def get(self, request, locale_code, app_code):
        appver = get_object_or_404(AppVersion, code=app_code)
        lang = get_object_or_404(Locale, code=locale_code)
        form = SignoffsPaginationForm(request.GET)
        if form.is_valid():
            next_push_date = form.cleaned_data['push_date']
        else:
            return HttpResponseBadRequest(str(form.errors))
        context = self.get_context_data(lang, appver, next_push_date)
        context['appver'] = appver
        html = render_to_string(
            self.template_name,
            context,
            context_instance=RequestContext(request)
        )
        if context['next_push_date']:
            next_push_date = context['next_push_date'].isoformat()
        else:
            next_push_date = None
        result = {
            'html': html,
            'pushes_left': context['pushes_left'],
            'next_push_date': next_push_date
        }
        return HttpResponse(
            json.dumps(result),
            content_type="application/json; charset=UTF-8"
        )

    def get_context_data(self, lang, appver, next_push_date):

        return self.annotated_pushes(
            lang,
            appver,
            next_push_date=next_push_date,
            count=self.count
        )


signoff_rows = SignoffRowsView.as_view()


def signoff_details(request, locale_code, app_code):
    """Details pane loaded on sign-off on a particular revision.

    Requires 'rev' in the query string, supports explicitly passing a 'run'.
    """
    try:
        # rev query arg is required, it's not a url param for caching, and
        # because it's dynamic in the js code, so the {% url %} tag prefers
        # this
        push_id = int(request.GET['push'])
    except (KeyError, ValueError):
        raise Http404
    try:
        # there might be a specified run parameter
        runid = int(request.GET['run'])
    except (KeyError, ValueError):
        runid = None
    # it is possible that this sign-off is the first one
    first = request.GET.get('first', 'false') == 'true'
    appver = get_object_or_404(AppVersion, code=app_code)
    lang = get_object_or_404(Locale, code=locale_code)
    push = get_object_or_404(Push, id=push_id)

    run = lastrun = None
    doubled = good = False

    cs = push.tip

    runs = (Run.objects.order_by('-pk')
            .filter(locale=lang, revisions=cs))
    q = None
    for avt in appver.trees_over_time.all():
        _q = {'tree': avt.tree_id}
        if avt.start:
            _q['srctime__gte'] = avt.start
        if avt.end:
            _q['srctime__lte'] = avt.end
        q = q is None and Q(**_q) or q | Q(**_q)
    if q is not None:
        runs = runs.filter(q)
        try:
            lastrun = runs[0]
        except IndexError:
            pass
    if runid is not None:
        try:
            run = Run.objects.get(id=runid)
        except Run.DoesNotExist:
            pass
    good = lastrun and (lastrun.errors == 0) and (lastrun.allmissing == 0)

    # check if we have a newer signoff.
    sos = appver.signoffs.filter(locale=lang, push__gte=push)
    sos = list(sos.annotate(la=Max('action')))
    newer = []
    if len(sos):
        s2a = dict((so.id, so.la) for so in sos)
        actions = Action.objects.filter(id__in=s2a.values())
        actions = dict((a.signoff_id, a.get_flag_display())
                       for a in actions)
        for so in sos:
            if so.push_id == push.id:
                doubled = True
                good = False
            else:
                flag = actions[so.id]
                if flag not in newer:
                    newer.append(flag)
                    good = False
        newer = sorted(newer)

    return render(request, 'shipping/signoff-details.html', {
                    'language': lang,
                    'run': run,
                    'good': good,
                    'doubled': doubled,
                    'newer': newer,
                    'first': first,
                    'accepts_signoffs': appver.accepts_signoffs,
                  })


@require_POST
def add_signoff(request, locale_code, app_code):
    """Actual worker to add a sign-off to the database.
    Requires shipping.add_signoff permission.
    """
    _redirect = redirect('shipping.views.signoff.signoff',
                         locale_code, app_code)
    if request.user.has_perm("shipping.add_signoff"):
        # permissions are cool, let's check the data
        try:
            lang = Locale.objects.get(code=locale_code)
            appver = AppVersion.objects.get(code=app_code)
            if not appver.accepts_signoffs:
                # we're not accepting signoffs, someone's hitting urls manually
                raise ValueError("not accepting signoffs for %s" %
                                 app_code)
            try:
                push_id = int(request.POST['push'])
            except (KeyError, ValueError), msg:
                return HttpResponseBadRequest(str(msg))
            push = Push.objects.get(id=push_id)
            if push.signoff_set.filter(appversion=appver).count():
                # there's already an existing sign-off, bail
                # messages.info(request, "There is already an existing
                # sign-off for this revision.")
                return _redirect
            # find a run, hopefully the one provided by the form
            runs = push.tip.run_set
            # XXX FIXME: this `run` instance is never used
            try:
                runid = int(request.POST['run'])
                try:
                    run = runs.get(id=runid)
                except Run.DoesNotExist:
                    run = runs.order_by('-build__id')[0]
            except:
                run = None
            so = Signoff.objects.create(push=push, appversion=appver,
                                        author=request.user, locale=lang)
            so.action_set.create(flag=Action.PENDING, author=request.user)
        except Exception, e:
            print(e)
            return _redirect
    return _redirect


@require_POST
def review_signoff(request, locale_code, app_code):
    """Actual worker to review a sign-off.
    Requires shipping.review_signoff permission.
    """
    _redirect = redirect('shipping.views.signoff.signoff',
                         locale_code, app_code)
    if request.user.has_perm("shipping.review_signoff"):
        # permissions are cool, let's check the data
        try:
            lang = Locale.objects.get(code=locale_code)
            appver = (AppVersion.objects
                      .select_related('tree').get(code=app_code))
            action = request.POST['action']
            signoff_id = int(request.POST['signoff_id'])
            flag = action == "accept" and Action.ACCEPTED or Action.REJECTED
        except Exception, e:
            # logging.error("review_signoff called without action")
            print(e)
            return _redirect

        # verify integrity, make sure we have a sign-off for app/locale/id
        try:
            so = appver.signoffs.get(locale=lang, id=signoff_id)
        except Signoff.DoesNotExist:
            # logging.error()
            print('no such signoff')
            return _redirect
        comment = request.POST.get('comment', '')
        clean_old = (flag is Action.REJECTED and
                     request.POST.get("clear_old", "no") == "yes")

        # actually do the work
        so.action_set.create(flag=flag, author=request.user, comment=comment)
        if clean_old:
            for _so in (appver.signoffs
                        .filter(locale=lang, id__lt=signoff_id)
                        .order_by('-pk')):
                _status = _so.status  # dynamic property, cache here
                if _status == Action.PENDING:
                    _so.action_set.create(flag=Action.CANCELED,
                                          author=request.user)
                else:
                    break
    return _redirect


@require_POST
def cancel_signoff(request, locale_code, appver_code):
    """Actual worker to cancel a pending sign-off.
    Requires shipping.add_signoff permission.
    """
    _redirect = redirect('shipping.views.signoff.signoff',
                         locale_code, appver_code)
    if not request.user.has_perm("shipping.add_signoff"):
        return _redirect

    lang = get_object_or_404(Locale, code=locale_code)
    appver = get_object_or_404(AppVersion, code=appver_code)

    # permissions are cool, let's check the data
    try:
        signoff_id = int(request.POST['signoff_id'])
        so = Signoff.objects.get(
            id=signoff_id,
            locale=lang,
            appversion=appver
        )
    except KeyError:
        return HttpResponseBadRequest("no 'signoff_id'")
    except ValueError:
        return HttpResponseBadRequest("not an integer")
    except Signoff.DoesNotExist:
        return HttpResponseBadRequest("Signoff not found")

    if so.status != Action.PENDING:
        return HttpResponseBadRequest("Signoff not pending (%s)" % so.flag)

    Action.objects.create(
        signoff=so,
        flag=Action.CANCELED,
        author=request.user,
    )

    return _redirect


@require_POST
def reopen_signoff(request, locale_code, appver_code):
    """Actual worker to reopen a canceled sign-off.
    Requires shipping.add_signoff permission.
    """
    _redirect = redirect('shipping.views.signoff.signoff',
                         locale_code, appver_code)
    if not request.user.has_perm("shipping.add_signoff"):
        return _redirect

    lang = get_object_or_404(Locale, code=locale_code)
    appver = get_object_or_404(AppVersion, code=appver_code)

    # permissions are cool, let's check the data
    try:
        signoff_id = int(request.POST['signoff_id'])
        so = Signoff.objects.get(
            id=signoff_id,
            locale=lang,
            appversion=appver
        )
    except KeyError:
        return HttpResponseBadRequest("no 'signoff_id'")
    except ValueError:
        return HttpResponseBadRequest("not an integer")
    except Signoff.DoesNotExist:
        return HttpResponseBadRequest("Signoff not found")

    if so.status != Action.CANCELED:
        return HttpResponseBadRequest("Signoff not canceled (%s)" % so.flag)

    Action.objects.create(
        signoff=so,
        flag=Action.PENDING,
        author=request.user,
    )

    return _redirect
