# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''APIs for managing sign-offs and shipping metrics.
'''


from collections import defaultdict

from life.models import Locale
from l10nstats.models import Run
from shipping.models import AppVersion, Signoff, Action

# allow to monkey patch the set of active locales
test_locales = []


def _actions4appversion(appversion, locales, chunk_size, up_until=None):
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
    # now we know which locales to check for this version, go for Actions
    actions = Action.objects.filter(signoff__appversion=appversion)
    if up_until:
        actions = actions.filter(when__lte=up_until)
    inc_locales = dict((id, set()) for id in locales)
    if len(inc_locales) < 10:
        # optimize for few locales use to actually reduce the actions
        actions = actions.filter(signoff__locale__in=inc_locales.keys())

    # reduce the queryset by sort order and only the data we need out
    actions = (actions.order_by('-signoff__id', '-id')
                       .values_list('id',
                                   'flag',
                                   'signoff_id',
                                   'signoff__locale_id'))
    i = 0
    rv = defaultdict(dict)  # return value
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


def actions4appversions(appversions, locales=None, chunk_size=100,
                        up_until=None):
    """Get actions for given appversions and locales.
    Returns a 4-level dictionary:
    appversions -> locale_id -> flag -> action_id
    """
    if locales is None:
        locales = {}

    if isinstance(locales, dict):
        #it's a search!
        locales = list(Locale.objects
                       .filter(**locales)
                       .values_list('id', flat=True)
                       .distinct())
    elif not isinstance(locales, (tuple, list)):
        # locales is neither list nor search, bail out
        raise NotImplementedError
    appversions = list(appversions)

    rv = {}  # return value
    fallbacks = {}  # locale sets that need fallback

    while appversions:
        appversion = appversions.pop()
        rv[appversion], not_found = \
            _actions4appversion(appversion,
                                fallbacks.get(appversion, locales),
                                chunk_size,
                                up_until=up_until)
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


def accepted_signoffs(appversion, up_until=None):
    """Get accepted sign-offs for a single appversion, including fallbacks.
    Returns a Signoffs query.
    The returned sign-offs don't necessarily need to be on the requested
    appversion, due to fallback.
    """
    flags4loc = (flags4appversions([appversion],
                                   up_until=up_until)
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


def flags4appversions(appversions, locales=None, up_until=None):
    """Get flags or fallback codes for given locales and appversions.
    Returns appversion -> locale__code -> (av__code, {flag -> action_id}).
    """
    # map to replace locale IDs with codes inside the helper
    loc4id = dict(Locale.objects.values_list('id', 'code'))
    flaglocs4av = actions4appversions(appversions,
        locales=locales,
        up_until=up_until
    )
    rv = {}
    while flaglocs4av:
        _flags4av(flaglocs4av, loc4id, rv)
    return rv
