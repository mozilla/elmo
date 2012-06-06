# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views centric around AppVersion data.
"""

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
    fallback = av.fallback
    while fallback and fallback in flags4av:
        flags4loc = flags4av[fallback]
        locs = [loc for loc, (real_av, flags) in flags4loc.iteritems()
                if (real_av == fallback.code and
                    loc not in current and
                    Action.ACCEPTED in flags)]
        if locs:
            # store actions for now, we'll get the push_ids later
            for loc in locs:
                current[loc] = flags4loc[loc][1][Action.ACCEPTED]
            rows.append({
                'name': str(fallback),
                'code': fallback.code,
                'changes': [(loc, 'added') for loc in sorted(locs)]
                })
        fallback = fallback.fallback
    rows.reverse()
    for loc, pid in (Signoff.objects
                     .filter(action__in=current.values())
                     .values_list('locale__code',
                                  'push__id')):
        current[loc] = pid
    for _mid, loc, pid in (Milestone_Signoffs.objects
                           .filter(milestone__appver=av)
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
                changes.sort(key=lambda t: t[0])
            latest = current
            current = {}
            ms_name = ms_names[ms_id]
            changes = []
            rows.append({'name': ms_name,
                         'code': ms_codes[ms_id],
                         'changes': changes})
        if loc not in latest:
            changes.append((loc, 'added'))
        else:
            lpid = latest.pop(loc)
            if lpid != pid:
                changes.append((loc, 'changed'))
        current[loc] = pid
    # see if we have some locales dropped in the last milestone
    if latest:
        # previous milestone has locales left, update previous changes
        changes += [(loc, 'dropped') for loc in latest.iterkeys()]
        changes.sort(key=lambda t: t[0])

    return render(request, 'shipping/app-changes.html', {
                    'appver': av,
                    'rows': rows,
                  })
