# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views centric around AppVersion data.
"""

from django.shortcuts import render, get_object_or_404
from shipping.models import Milestone, AppVersion, Milestone_Signoffs


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
