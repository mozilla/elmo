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
#   Axel Hecht <l10n@mozilla.com>
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

'''APIs for managing sign-offs and shipping metrics.
'''


from collections import defaultdict

from life.models import Locale
from shipping.models import AppVersion, Signoff, Action


def signoff_actions(locales=None, appversions=None, chunk_size=100):
    if locales is None:
        locales = {}
    if appversions is None:
        appversions = {}
    # go over all appversions
    appversions = AppVersion.objects.filter(**appversions)
    for appversion in appversions.select_related("tree"):
        # all specified locales
        locales_q = Locale.objects.filter(**locales)
        # XXX data2: reduce to active locales for the appversion
        active_locs = locales_q
        # included locales for which we still need to gather more data
        # maps locale id to signoff ids we collected, starting with an
        # empty set
        inc_locales = dict((_id, set())
                           for _id in active_locs.values_list('id', flat=True))

        # now we know which locales to check for this version, go for Actions
        actions = (Action.objects
                   .filter(signoff__appversion=appversion)
                   .order_by('-signoff__id', '-id')
                   .values_list('id',
                                'flag',
                                'signoff_id',
                                'signoff__locale_id'))
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
                if action_flag == Action.OBSOLETED:
                    # this signoff is obsolete, this locale is covered
                    inc_locales.pop(loc_id, None)
                    # not sure if to notify?
                    continue
                inc_locales[loc_id].add(signoff_id)
                if action_flag == Action.CANCELED:
                    # this signoff is cancelled, continue handle this locale,
                    # but not notify
                    continue
                if action_flag == Action.ACCEPTED:
                    # this signoff is accepted, this locale is covered
                    inc_locales.pop(loc_id, None)
                # notify about this signoff action
                yield action_id, action_flag
            if not had_action:
                break


def flag_lists(locales=None, appversions=None, chunk_size=100):
    actions = dict(signoff_actions(locales=locales,
                                   appversions=appversions,
                                   chunk_size=chunk_size))
    flags = defaultdict(list)
    actions = Action.objects.filter(id__in=actions.keys())
    for tree, loc, f in actions.values_list('signoff__appversion__tree__code',
                                            'signoff__locale__code',
                                            'flag'):
        if f not in flags[tree, loc]:
            flags[tree, loc].append(f)
    return flags


def accepted_signoffs(**avq):
    actions = [a_id for a_id, flag in
               signoff_actions(appversions=avq)
               if flag == Action.ACCEPTED]
    return Signoff.objects.filter(action__in=actions)
