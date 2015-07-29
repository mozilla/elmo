# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views centric around AppVersion data.
"""

from collections import defaultdict
from django.shortcuts import render, get_object_or_404
from shipping.models import (Milestone, AppVersion, Milestone_Signoffs,
                             Action, Signoff)
from shipping.api import flags4appversions


def changes(request, app_code):
    """Show which milestones on the given appversion took changes for which
    locale
    """
    av = get_object_or_404(AppVersion, code=app_code)
    ms_names = {}
    ms_codes = {}
    for ms in (Milestone.objects
               .filter(appver=av)
               .select_related('appver__app')):
        ms_names[ms.id] = str(ms)
        ms_codes[ms.id] = ms.code
    rows = []
    changes = None
    ms_id = None
    latest = {}
    current = {}
    ms_name = None
    # get historic data that enters this appversion
    # get that in fallback order, we'll reverse afterwards
    flags4av = flags4appversions(appversions={"id": av.id})
    flags4loc = flags4av[av]
    locs4av = defaultdict(dict)  # av -> loc -> ACCEPTED
    notaccepted = {}  # av -> flags
    for loc, (real_av, flags) in flags4loc.iteritems():
        if Action.ACCEPTED in flags:
            locs4av[real_av][loc] = flags[Action.ACCEPTED]
        else:
            notaccepted[loc] = flags
    # for not accepted locales on the current appver,
    # check for accepted on fallbacks
    if av.fallback and notaccepted:
        flags4fallback = flags4av[av.fallback]
        for loc in notaccepted:
            if loc in flags4fallback:
                # if the loc isn't here, it's never been accepted so far
                real_av, flags = flags4fallback[loc]
                if Action.ACCEPTED in flags:
                    locs4av[real_av] = flags[Action.ACCEPTED]
    # let's keep the current appver data around for later,
    # and order the fallbacks.
    # Also, keep track of how many locales fell back to
    #  * the previous cycle
    #  * the two cycles before that (2 and 3)
    #  * older cycles (4 and more)
    accepted = locs4av.pop(av.code, {})
    av_ = av
    fallback = 0  # how deep are we falling back
    buckets = {0: 0, 1: 1, 2: 2, 3: 2}  # which fallback to which bucket
    bucket = 0  # bucket we're in
    rowspan = 0  # how many rows are in this bucket
    locales_group = set()  # which locales are in this bucket
    while av_ and locs4av:
        thisbucket = buckets.get(fallback, 3)
        if thisbucket != bucket and locales_group:
            rows[-1].update({
                'rowspan': rowspan,
                'group_locales_count': len(locales_group)
                })
            locales_group.clear()
            rowspan = 0
        bucket = thisbucket
        if av_.code in locs4av:
            accepted4loc = locs4av.pop(av_.code)
            # store actions for now, we'll get the push_ids later
            current.update(accepted4loc)
            locales_group.update(accepted4loc.keys())
            rowspan += 1
            rows.append({
                'name': str(av_),
                'code': av_.code,
                'isAppVersion': True,
                'changes': [(loc, 'added') for loc in sorted(accepted4loc)]
                })
        av_ = av_.fallback
        fallback += 1
    if locales_group and rows:
        rows[-1].update({
            'rowspan': rowspan,
            'group_locales_count': len(locales_group)
            })
    rows.reverse()
    for loc, pid in (Signoff.objects
                     .filter(action__in=current.values())
                     .values_list('locale__code',
                                  'push__id')):
        current[loc] = pid
    for loc, pid in (Signoff.objects
                     .filter(action__in=accepted.values())
                     .values_list('locale__code',
                                  'push__id')):
        accepted[loc] = pid
    # reset group data for the current appversion, all one group
    avrow = None  # keep track of the first row
    rowspan = 0
    locales_group.clear()
    current = {}
    # we're only doing sign-offs for this appversion now, and for milestones
    # of this appversion
    for _mid, loc, pid in (Milestone_Signoffs.objects
                           .filter(milestone__appver=av)
                           .filter(signoff__appversion=av)
                           .order_by('milestone__id',
                                     'signoff__locale__code')
                           .values_list('milestone__id',
                                        'signoff__locale__code',
                                        'signoff__push__id')):
        if _mid != ms_id:
            ms_id = _mid
            # next milestone, bootstrap new row
            if latest:
                # previous milestone has locales left, update previous changes
                changes += [(_loc, 'dropped') for _loc in latest.iterkeys()]
                changes.sort()
            latest = current
            current = {}
            ms_name = ms_names[ms_id]
            changes = []
            rows.append({'name': ms_name,
                         'code': ms_codes[ms_id],
                         'changes': changes})
            rowspan += 1
            if avrow is None:
                avrow = rows[-1]
        if loc not in latest:
            changes.append((loc, 'added'))
            locales_group.add(loc)
        else:
            lpid = latest.pop(loc)
            if lpid != pid:
                changes.append((loc, 'changed'))
        current[loc] = pid

    # see if we have some locales dropped in the last milestone
    if latest:
        # previous milestone has locales left, update previous changes
        changes += [(loc, 'dropped') for loc in latest.iterkeys()]
        changes.sort()
    # add group info to the avrow
    if avrow:
        avrow.update({
            'rowspan': rowspan,
            'rowspan_last': True,
            'group_locales_count': len(locales_group)
            })
    # finally, check if there's more signoffs after the last shipped milestone
    newso = [(loc, loc in current and 'changed' or 'added')
        for loc, pid in accepted.iteritems()
        if current.get(loc) != pid]
    for loc, flags in notaccepted.iteritems():
        if Action.PENDING in flags:
            newso.append((loc, 'pending'))
        elif Action.REJECTED in flags:
            newso.append((loc, 'rejected'))
        elif Action.OBSOLETED in flags:
            newso.append((loc, 'obsoleted'))
    if newso:
        newso.sort()
        rows.append({
            'name': '%s .next' % str(av),
            'changes': newso
        })
        addcount = len([t for t in newso if t[1]=='added'])
        if addcount:
            rows[-1].update({
                'rowspan': 1,
                'rowspan_last': True,
                'group_locales_count': '+%d' % addcount
            })

    return render(request, 'shipping/app-changes.html', {
                    'appver': av,
                    'rows': rows,
                  })
