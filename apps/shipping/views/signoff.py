# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views and helpers for sign-off views.
"""


from django.db.models import Max, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
# TODO: from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST, etag
from django.views.decorators import cache

from life.models import Locale, Push
from shipping.models import AppVersion, Signoff, Action
from shipping.api import flags4appversions, annotated_pushes
from l10nstats.models import Run


def etag_signoff(request, locale_code, app_code):
    """The signoff view should update for:
    - new actions
    - new pushes
    - new runs on existing pushes
    - changed permissions
    """
    try:
        av = AppVersion.objects.get(code=app_code)
    except AppVersion.DoesNotExist:
        # bad request, turn off etags, that's simple
        return None

    def get_id_or_null(q):
        # helper to get the first id, or 0
        try:
            return q.values_list('id', flat=True)[0]
        except IndexError:
            return 0

    actions = Action.objects.filter(signoff__locale__code=locale_code,
                                    signoff__appversion=av).order_by('-pk')
    # pushes and runs only matter if there's still a tree associated
    # just check the current tree
    try:
        tree_id = av.trees_over_time.current().values_list('id', flat=True)[0]
    except IndexError:
        tree_id = None
    if tree_id:
        pushes = (Push.objects
                  .filter(repository__forest__tree=tree_id)
                  .filter(repository__locale__code=locale_code)
                  .order_by('-pk'))
        runs = (Run.objects
                .filter(tree=tree_id)
                .filter(locale__code=locale_code)
                .order_by('-pk'))
        ids = tuple(map(get_id_or_null, (actions, pushes, runs)))
    else:
        ids = (get_id_or_null(actions), 0, 0)
    can_signoff = request.user.has_perm('shipping.add_signoff')
    review_signoff = request.user.has_perm('shipping.review_signoff')

    return "%d|%d|%d|%d|%d" % ((can_signoff, review_signoff) + ids)


#@cache.cache_control(private=True)
#@etag(etag_signoff)
def signoff(request, locale_code, app_code):
    """View to show recent sign-offs and opportunities to sign off.

    This view is the main entry point to localizers to add sign-offs and to
    review what they're shipping.
    It's also the entry point for drivers to review existing sign-offs.
    """
    appver = get_object_or_404(AppVersion, code=app_code)
    lang = get_object_or_404(Locale, code=locale_code)
    # which pushes to show
    real_av, flags = (flags4appversions(
        locales={'id': lang.id},
        appversions={'id': appver.id})
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

    pushes, suggested_signoff = annotated_pushes(appver, lang, actions, flags)
    if real_av != appver.code and accepted is not None:
        # we're falling back, add the accepted push to the table
        fallback = accepted
    else:
        fallback = None

    return render(request, 'shipping/signoffs.html', {
                    'appver': appver,
                    'language': lang,
                    'pushes': pushes,
                    'pending': pending,
                    'rejected': rejected,
                    'accepted': accepted,
                    'suggested_signoff': suggested_signoff,
                    'login_form_needs_reload': True,
                    'fallback': fallback,
                    'real_av': real_av,
                  })


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
                    'run': run,
                    'good': good,
                    'doubled': doubled,
                    'newer': newer,
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
            print e
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
            print e
            return _redirect

        # verify integrity, make sure we have a sign-off for app/locale/id
        try:
            so = appver.signoffs.get(locale=lang, id=signoff_id)
        except Signoff.DoesNotExist:
            # logging.error()
            print 'no such signoff'
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
