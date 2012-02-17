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

from life.models import Locale, Push, Push_Changesets
from l10nstats.models import Run, Run_Revisions
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
        if len(inc_locales) == 1:
            # optimize for single-locale use to actually reduce the actions
            actions = actions.filter(signoff__locale__id=inc_locales.keys()[0])
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

    # ordering by `-id` means that the most *recent* actions appear first
    actions = Action.objects.filter(id__in=actions.keys()).order_by('-id')

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


def signoff_summary(actions):
    """get current status of signoffs"""
    pending = rejected = accepted = None
    all_actions = sorted(actions, key=lambda _a: -_a.signoff.id)
    initial_diff = []
    for action in all_actions:
        flag = action.flag
        _so = action.signoff
        if flag == Action.PENDING:  # keep if there's no pending or rejected
            if pending is None and rejected is None:
                pending = _so.push
                if len(initial_diff) < 2:
                    initial_diff.append(_so.id)
            continue
        elif flag == Action.ACCEPTED:  # store and don't look any further
            accepted = _so.push
            if len(initial_diff) < 2:
                initial_diff.append(_so.id)
            break
        elif flag == Action.REJECTED:  # keep, if there's no rejected
            if rejected is None:
                rejected = _so.push
                if len(initial_diff) < 2:
                    initial_diff.append(_so.id)
            continue
        elif flag == Action.OBSOLETED:  # obsoleted, stop looking
            break
        else:
            # flag == Action.CANCELED, ignore, keep looking
            pass
    return pending, rejected, accepted, initial_diff


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
                                'who': push.user,
                                'when': push.push_date,
                                'url': push.repository.url,
                                'id': cs.shortrev})
            self.rowcount = 0
            self._prev = push.id


def annotated_pushes(repo, appver, loc, actions, initial_diff=None, count=10):
    if initial_diff == None:
        initial_diff = []
    pushes_q = (Push.objects
                .filter(changesets__branch__id=1)
                .order_by('-push_date'))
    pushes_q = pushes_q.filter(repository=repo)
    current_so = currentpush = None
    actions4push = defaultdict(list)
    for action in actions:
        if action.flag == Action.ACCEPTED:
            current_so = action.signoff
            currentpush = current_so.push_id
        actions4push[action.signoff.push_id].append(action)
    if current_so is not None:
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

    pushes = _RowCollector(pcs, actions4push).pushes

    # get latest runs for our changesets
    csl = list(pcs.values_list('changeset__id', flat=True))
    rrs = Run_Revisions.objects.filter(run__tree=appver.tree_id,
                                       run__locale=loc,
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

    return pushes, currentpush, suggested_signoff
