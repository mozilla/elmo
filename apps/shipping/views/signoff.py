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

"""Views and helpers for sign-off views.
"""

from collections import defaultdict

from django.db.models import Max
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.conf import settings
# TODO: from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST, etag

from life.models import Repository, Locale, Push, Changeset, Push_Changesets
from shipping.models import AppVersion, Signoff, Action
from shipping.api import signoff_actions
from l10nstats.models import Run, Run_Revisions


class _RowCollector:
    """Helper class to collect all the rows and tests etc for a Push_Changesets query.
    """
    def __init__(self, pcs, actions4push):
        """Create _RowCollector and do the work. Result is in self.pushes.

        pcs is a Push_Changesets queryset, ordered by -push_date, -changeset_id
        actions4push is a dict mapping push ids to lists of action objects

        The result is a list of dictionaries, describing the table rows to be shown for each push,
        as well as the detail information within.
        """
        self.actions4push = actions4push
        self.pushes = []
        self._prev = None
        self.rowcount = 0
        for _pc in pcs.select_related('push__repository','changeset'):
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
            self.pushes.append({'changes':[],
                                'who': push.user,
                                'when': push.push_date,
                                'url': push.repository.url,
                                'id': cs.shortrev})
            self.rowcount = 0
            self._prev = push.id


def etag_signoff(request, locale_code, app_code):
    actions = Action.objects.filter(signoff__locale__code=locale_code,
                                    signoff__appversion__code=app_code).order_by('-pk')
    can_signoff = request.user.has_perm('shipping.add_signoff')
    review_signoff = request.user.has_perm('shipping.review_signoff')
    try:
        _id = str(actions.values_list('id',flat=True)[0])
    except IndexError:
        _id = "no signoff"
    return "%d|%d|%s" % (can_signoff, review_signoff, _id)

@etag(etag_signoff)
def signoff(request, locale_code, app_code):
    """View to show recent sign-offs and opportunities to sign off.

    This view is the main entry point to localizers to add sign-offs and to review
    what they're shipping.
    It's also the entry point for drivers to review existing sign-offs.
    """
    appver = get_object_or_404(AppVersion, code=app_code)
    lang = get_object_or_404(Locale, code=locale_code)
    forest = appver.tree.l10n
    repo = get_object_or_404(Repository, locale=lang, forest=forest)
    # which pushes to show
    pushes_q = Push.objects.order_by('-push_date').filter(changesets__branch__id=1)
    pushes_q = pushes_q.filter(repository=repo)
    actions = list(a_id for a_id, flag in \
                   signoff_actions(appversions={'id': appver.id},
                                   locales={'id': lang.id}))
    actions = list(Action.objects.filter(id__in=actions)
                   .select_related('signoff__push', 'author'))
    current_so = currentpush = None
    actions4push = defaultdict(list)
    for action in actions:
        if action.flag == Action.ACCEPTED:
            current_so = action.signoff
            currentpush = current_so.push_id
        actions4push[action.signoff.push_id].append(action)
    if current_so is not None:
        pushes_q = pushes_q.filter(push_date__gte=current_so.push.push_date).distinct()
    else:
        pushes_q = pushes_q.distinct()[:10]

    # get pushes, changesets and signoffs/actions
    _p = list(pushes_q.values_list('id',flat=True))
    pcs = Push_Changesets.objects.filter(push__in=_p).order_by('-push__push_date','-changeset__id')

    pushes = _RowCollector(pcs, actions4push).pushes

    # get current status of signoffs
    pending = rejected = accepted = None
    all_actions = sorted(actions, key=lambda _a: -_a.signoff.id)
    initial_diff = []
    for action in all_actions:
        flag = action.flag
        _so = action.signoff
        if flag == Action.PENDING: # keep if there's no pending or rejected
            if pending is None and rejected is None:
                pending = _so.push
                if len(initial_diff) < 2:initial_diff.append(_so.id)
            continue
        elif flag == Action.ACCEPTED: # store and don't look any further
            accepted = _so.push
            if len(initial_diff) < 2:initial_diff.append(_so.id)
            break
        elif flag == Action.REJECTED: # keep, if there's no rejected
            if rejected is None:
                rejected = _so.push
                if len(initial_diff) < 2:initial_diff.append(_so.id)
            continue
        elif flag == Action.OBSOLETED: # obsoleted, stop looking
            break
        else:
            # flag == Action.CANCELED, ignore, keep looking
            pass

    # get latest runs for our changesets
    csl = list(pcs.values_list('changeset__id', flat=True))
    rrs = Run_Revisions.objects.filter(run__tree=appver.tree_id,
                                       run__locale=lang,
                                       changeset__in=csl)
    rrs = rrs.order_by('changeset', 'run')
    c2r = dict(rrs.values_list('changeset', 'run'))
    r2r = dict((r.id, r) for r in (Run.objects
                                   .filter(id__in=c2r.values())
                                   .select_related('build')))

    # merge data back into pushes list
    suggested_signoff = None
    # initial_diff and runs
    if len(initial_diff) < 2 and pushes:
        pushes[0]['changes'][0].diffbases = [None] * (2 - len(initial_diff))
    for p in pushes:
        # initial_diff
        for sod in p['signoffs']:
            if sod['signoff'].id in initial_diff:
                sod['diffbases'] = 1
        # runs
        for c in p['changes']:
            if c.id in c2r and c2r[c.id] is not None:
                # we stored a run for a changeset in this push
                _r = r2r[c2r[c.id]]
                p['run'] = _r
                # should we suggest this?
                if suggested_signoff is None:
                    if p['signoffs']:
                        # last good push is signed off, don't suggest anything
                        suggested_signoff = False
                    elif _r.allmissing == 0 and _r.errors == 0:
                        # source checks are good, suggest
                        suggested_signoff = p['id']

    return render_to_response('shipping/signoffs.html',
                              {'appver': appver,
                               'language': lang,
                               'pushes': pushes,
                               'current': currentpush,
                               'pending': pending,
                               'rejected': rejected,
                               'accepted': accepted,
                               'tree': appver.tree.code,
                               'repo': repo,
                               'suggested_signoff': suggested_signoff,
                               'login_form_needs_reload': True,
                               'request': request,
                               },
                              context_instance=RequestContext(request))


def signoff_details(request, locale_code, app_code):
    """Details pane loaded on sign-off on a particular revision.

    Requires 'rev' in the query string, supports explicitly passing a 'run'.
    """
    try:
        # rev query arg is required, it's not a url param for caching, and because it's dynamic
        # in the js code, so the {% url %} tag prefers this
        rev = request.GET['rev']
    except:
        raise Http404
    try:
        # there might be a specified run parameter
        runid = int(request.GET['run'])
    except:
        runid = None
    appver = get_object_or_404(AppVersion, code=app_code)
    lang = get_object_or_404(Locale, code=locale_code)
    forest = appver.tree.l10n
    repo = get_object_or_404(Repository, locale=lang, forest=forest)

    run = lastrun = None
    good = False
    try:
        cs = repo.changesets.get(revision__startswith=rev)
    except Changeset.DoesNotExist:
        cs = None
    if cs is not None:
        runs = Run.objects.order_by('-pk').filter(tree=appver.tree_id, locale=lang, revisions=cs)
        if runid is not None:
            try:
                run = runs.get(id=runid)
            except Run.DoesNotExist:
                pass
        try:
            lastrun = runs[0]
        except IndexError:
            pass
        good = lastrun and (lastrun.errors == 0) and (lastrun.allmissing == 0)

        # check if we have a newer signoff.
        push = cs.pushes.get(repository=repo)
        sos = appver.signoffs.filter(locale=lang, push__gte=push)
        sos = list(sos.annotate(la=Max('action')))
        doubled = None
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

    return render_to_response('shipping/signoff-details.html',
                              {
                                  'run': run,
                                  'good': good,
                                  'doubled': doubled,
                                  'newer': newer,
                               })

@require_POST
def add_signoff(request, locale_code, app_code):
    """Actual worker to add a sign-off to the database.
    Requires shipping.add_signoff permission.
    """
    _redirect = redirect('shipping.views.signoff.signoff', locale_code, app_code)
    if request.user.has_perm("shipping.add_signoff"):
        # permissions are cool, let's check the data
        try:
            lang = Locale.objects.get(code=locale_code)
            appver = AppVersion.objects.select_related('tree').get(code=app_code)
            repo = Repository.objects.get(locale=lang, forest=appver.tree.l10n_id)
            rev = request.POST['revision']
            push = Push.objects.get(repository=repo, changesets__revision__startswith=rev)
            if push.signoff_set.filter(appversion=appver).count():
                # there's already an existing sign-off, bail
                # messages.info(request, "There is already an existing sign-off for this revision.")
                return _redirect
            # find a run, hopefully the one provided by the form
            runs = push.tip.run_set
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
    _redirect = redirect('shipping.views.signoff.signoff', locale_code, app_code)
    if request.user.has_perm("shipping.review_signoff"):
        # permissions are cool, let's check the data
        try:
            lang = Locale.objects.get(code=locale_code)
            appver = AppVersion.objects.select_related('tree').get(code=app_code)
            repo = Repository.objects.get(locale=lang, forest=appver.tree.l10n_id)
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
        clean_old = flag is Action.REJECTED and request.POST.get("clear_old", "no") == "yes"

        # actually do the work
        so.action_set.create(flag=flag, author=request.user, comment=comment)
        if clean_old:
            for _so in appver.signoffs.filter(locale=lang, id__lt=signoff_id).order_by('-pk'):
                _status = _so.status # dynamic property, cache here
                if _status == Action.PENDING:
                    _so.action_set.create(flag=Action.CANCELED, author=request.user)
                else:
                    break
    return _redirect
