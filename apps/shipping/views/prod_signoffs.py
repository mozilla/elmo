# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views and helpers for PM sign-off views.
"""
from __future__ import absolute_import, print_function
from __future__ import unicode_literals

from collections import OrderedDict
import json

from django.http import HttpResponse
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView, View
from django.shortcuts import get_object_or_404
from django.db.models import Max

from shipping.models import (
    AppVersion,
    Action,
)
from life.models import (
    Changeset,
    Locale,
    Repository,
    Push,
)
from l10nstats.models import (
    Run,
)
from shipping.api import (
    flags4appversions,
)


class SignoffTableView(TemplateView):

    template_name = 'shipping/prod-signoffs.html'

    def get(self, request, appver_code):
        appver = get_object_or_404(AppVersion, code=appver_code)
        context = self.get_context_data(appver)
        return self.render_to_response(context)

    def get_context_data(self, appver):
        # av -> loc code -> [av_code, {flag -> action}]
        # Resolve the av key right away
        flags = flags4appversions([appver])[appver]
        flags = {
            loc: flag_actions.values()
            for loc, (_, flag_actions) in flags.items()
        }
        all_actions = []
        for actions in flags.values():
            all_actions += actions
        locales = (
            Locale.objects
            .filter(
                code__in=flags.keys(),
            )
        )
        l2so = dict(
            locales
            .filter(
                repository__push__signoff__action__in=all_actions
            )
            .annotate(last_signoff=Max('repository__push'))
            .values_list('code', 'last_signoff')
        )
        repos = Repository.objects.filter(push__in=l2so.values())
        l2p = dict(
            locales
            .filter(
                repository__in=repos
            )
            .annotate(last_push=Max('repository__push'))
            .values_list('code', 'last_push')
        )
        locale_count = len(flags)
        push_ids = set()
        revs_for_runs = set()
        rows = OrderedDict()
        for loc in sorted(l2p):
            if l2p[loc] == l2so[loc]:
                # latest push has sign-off data
                continue
            rows[loc] = {
                'push': l2p[loc],
                'signoff': l2so[loc],
                'tip': l2p[loc],
            }
            push_ids.update((l2so[loc], l2p[loc]))
        p2tip = {
            id_: {
                'name': name,
                'cs': last,
            }
            for id_, name, last in
            Push.objects
            .filter(id__in=push_ids)
            .annotate(last=Max('changesets'))
            .values_list('id', 'repository__name', 'last')
        }
        cs2rev = dict(
            Changeset.objects
            .filter(id__in=(t['cs'] for t in p2tip.values()))
            .values_list('id', 'revision')
        )
        for row in rows.values():
            row['repo'] = p2tip[row['tip']]['name']
            revs_for_runs.add(p2tip[row['tip']]['cs'])
            for p in ('signoff', 'tip'):
                row[p] = cs2rev[p2tip[row[p]]['cs']]
        trees = self.get_compare(appver, revs_for_runs, rows)
        return {
            'appver': appver,
            'trees': trees,
            'total_count': locale_count,
            'rows': rows,
        }

    def get_compare(self, appver, revs, rows):
        tree = appver.trees_over_time.current()[0].tree
        runs = {
            run.locale.code: run
            for run in Run.objects.filter(
                revisions__in=revs,
                tree=tree,
            ).select_related('locale')
        }
        for loc, row in rows.items():
            row['runs'] = [runs.get(loc)]
        return [tree]


class SignOffView(PermissionRequiredMixin, View):

    permission_required = ('shipping.add_signoff', 'shipping.review_signoff')

    def post(self, request, av_code, loc_code, push_id, **kwargs):
        av = get_object_or_404(AppVersion, code=av_code)
        loc = get_object_or_404(Locale, code=loc_code)
        push = get_object_or_404(Push, id=int(push_id))
        action = (
            Action.ACCEPTED if request.GET.get('action') == 'accepted'
            else
            Action.REJECTED
        )
        so = av.signoffs.create(push=push, author=request.user, locale=loc)
        so.action_set.create(flag=Action.PENDING, author=request.user)
        action = so.action_set.create(flag=action, author=request.user)
        result = {
            "signoff_id": so.id,
            "latest_action_id": action.id,
        }
        return HttpResponse(
            json.dumps(result),
            content_type="application/json; charset=UTF-8"
        )
