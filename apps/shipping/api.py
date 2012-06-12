# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''APIs for managing sign-offs and shipping metrics.
'''


from collections import defaultdict

from django.db.models import Q

from life.models import Repository, Locale, Push, Push_Changesets
from l10nstats.models import Run_Revisions, Run
from shipping.models import AppVersion, Signoff, Action

# allow to monkey patch the set of active locales
test_locales = []


def _actions4appversion(appversion, locales, chunk_size):
    '''Helper method, get the actions/flags for each of the given locales
    Also return the locales not found

    Params:
    appversion: AppVersion object, should have app and fallback cached
    locales: iterable of Locale ids
    chunk_size: size of chunks to iter over actions
    '''
    if locales is None:
        # we're not restricting locales
        # let's see which are working on this app or active
        latest_tree = appversion.trees_over_time.latest().tree
        locales = list(Run.objects
                       .filter(tree=latest_tree,
                               active__isnull=False)
                       .values_list('locale', flat=True)
                       .distinct())
    if test_locales:
        locales += test_locales
    rv = defaultdict(dict)  # return value
    inc_locales = dict((id, set()) for id in locales)
    # now we know which locales to check for this version, go for Actions
    actions = (Action.objects
               .filter(signoff__appversion=appversion)
               .order_by('-signoff__id', '-id')
               .values_list('id',
                            'flag',
                            'signoff_id',
                            'signoff__locale_id'))
    if len(inc_locales) < 10:
        # optimize for few locales use to actually reduce the actions
        actions = actions.filter(signoff__locale__in=inc_locales.keys())
    i = 0
    while inc_locales:
        actions_chunk = actions[chunk_size * i:chunk_size * (i + 1)]
        had_action = False
        i += 1
        for (action_id, action_flag,
             signoff_id, loc_id) in actions_chunk:
            had_action = True
            if loc_id not in inc_locales:
                # we handled this locale in this chunk, ignore it
                continue
            if signoff_id in inc_locales[loc_id]:
                # we already sent out an action for this signoff
                continue
            inc_locales[loc_id].add(signoff_id)
            if action_flag == Action.CANCELED:
                # this signoff is cancelled, continue handle this locale,
                # but not notify
                continue
            if action_flag in (Action.ACCEPTED, Action.OBSOLETED):
                # this signoff is accepted or obsoleted,
                # this locale is covered
                inc_locales.pop(loc_id, None)
            # notify about this signoff action
            rv[loc_id][action_flag] = rv[loc_id].get(action_flag, action_id)
        if not had_action:
            break
    return dict(rv), set(inc_locales.keys())


def actions4appversions(locales=None, appversions=None, chunk_size=100):
    """Get actions for given appversions and locales.
    Returns a 4-level dictionary:
    appversions -> locale_id -> flag -> action_id
    """
    if locales is None:
        locales = {}
    if appversions is None:
        appversions = {}

    if locales is not None:
        if isinstance(locales, dict):
            #it's a search!
            locales = list(Locale.objects
                           .filter(**locales)
                           .values_list('id', flat=True)
                           .distinct())
        elif not isinstance(locales, (tuple, list)):
            # locales is neither list nor search, bail out
            raise NotImplementedError
    if isinstance(appversions, dict):
        # it's a search
        appversions = list(AppVersion.objects
                          .filter(**appversions)
                          .order_by('id')
                          .select_related('app', 'fallback'))
    else:
        appversions = list(appversions)

    rv = {}  # return value
    fallbacks = {}  # locale sets that need fallback

    while appversions:
        appversion = appversions.pop()
        rv[appversion], not_found = \
            _actions4appversion(appversion,
                                fallbacks.get(appversion, locales),
                                chunk_size)
        # optimization:
        # if we need to fallback, only search for the not_found locales,
        # if possible
        if not_found and appversion.fallback:
            fb = appversion.fallback
            # if we still need to process the fallback, just do it in full
            if fb in appversions:
                # we're already scheduled to process this appversion
                # either it's going through the full list
                # or two appversions fall back to this, then update the set
                if fb in fallbacks:
                    fallbacks[fb].update(not_found)
            else:
                # we're only hitting the fallback appversion for fallback
                # only process not_found locales
                fallbacks[fb] = not_found
                appversions.insert(0, fb)
    return rv


def accepted_signoffs(appversion):
    """Get accepted sign-offs for a single appversion, including fallbacks.
    Returns a Signoffs query.
    The returned sign-offs don't necessarily need to be on the requested
    appversion, due to fallback.
    """
    flags4loc = (flags4appversions(appversions={'id': appversion.id})
                 .get(appversion, {}))
    actions = [flags[Action.ACCEPTED] for _, flags in flags4loc.itervalues()
               if Action.ACCEPTED in flags]
    return Signoff.objects.filter(action__in=actions)


def _flags4av(flaglocs4av, loc4id, rv, av=None):
    """Internal helper method for flags4appversions.
    Makes sure to get all fallbacks before processing an av via recursion.
    """
    if av is None:
        av = flaglocs4av.iterkeys().next()
    fallback = av.fallback
    flagdict4loc = flaglocs4av.pop(av)
    _rv = {}
    # ensure that we already have our fallback data, if needed
    if fallback is not None:
        if fallback not in rv and fallback in flaglocs4av:
            _flags4av(flaglocs4av, loc4id, rv, fallback)
        # got fallback data, only take those that are accepted
        if fallback in rv:
            for loc, (real_av, flags) in rv[fallback].iteritems():
                if Action.ACCEPTED in flags:
                    _rv[loc] = [real_av,
                                {Action.ACCEPTED: flags[Action.ACCEPTED]}]
    for locid, action4flag in flagdict4loc.iteritems():
        loc = loc4id[locid]
        if Action.OBSOLETED in action4flag:
            _rv.pop(loc, None)
        elif Action.ACCEPTED in action4flag or loc not in _rv:
            _rv[loc] = [av.code, action4flag.copy()]
        else:
            _rv[loc][1].update(action4flag)
    rv[av] = _rv


def flags4appversions(locales=None, appversions=None):
    """Get flags or fallback codes for given locales and appversions.
    Returns appversion -> locale__code -> (av__code, {flag -> action_id}).
    """
    # map to replace locale IDs with codes inside the helper
    loc4id = dict(Locale.objects.values_list('id', 'code'))
    flaglocs4av = actions4appversions(locales=locales, appversions=appversions)
    rv = {}
    while flaglocs4av:
        _flags4av(flaglocs4av, loc4id, rv)
    return rv


class _RowCollector:
    """Helper class to collect all the rows and tests etc for a
    Push_Changesets query.
    """
    def __init__(self, pcs, actions4push):
        """Create _RowCollector and do the work. Result is in self.pushes.

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
                                'who': push.user,
                                'when': push.push_date,
                                'repo': push.repository.name,
                                'url': push.repository.url,
                                'forest': push.repository.forest_id,
                                'id': cs.shortrev})
            self.rowcount = 0
            self._prev = push.id


def annotated_pushes(appver, loc, actions, flags, fallback, count=10):
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
                               locale=loc)
                       .values_list('forest', 'id'))
    repoquery = None
    for (_s, _e), _f in forest4times.iteritems():
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
    current_so = None
    action4id = dict((a.id, a) for a in actions)
    initial_diff = []
    if Action.ACCEPTED in flags:
        a = action4id[flags[Action.ACCEPTED]]
        current_so = a.signoff
        initial_diff.append(a.signoff_id)
    if Action.PENDING in flags:
        initial_diff.append(action4id[flags[Action.PENDING]].signoff_id)
    if Action.REJECTED in flags and len(initial_diff) < 2:
        initial_diff.append(action4id[flags[Action.REJECTED]].signoff_id)
    # if we're having a sign-off on this appversion, i.e no fallback,
    # show only new pushes
    if current_so is not None and fallback is None:
        pushes_q = (pushes_q
                    .filter(push_date__gte=current_so.push.push_date)
                    .distinct())
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
    pushes = _RowCollector(pcs, actions4push).pushes

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
                       run__locale=loc,
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
    if len(initial_diff) < 2 and pushes:
        pushes[0]['changes'][0].diffbases = [None] * (2 - len(initial_diff))
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

    return pushes, suggested_signoff
