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

from collections import defaultdict
import re

from django import http
from django.shortcuts import get_object_or_404
try:
    import json
except:
    from django.utils import simplejson as json

from life.models import Repository, Changeset, Push, Branch


def jsonify(_v):
    def _wrapped(request, *args, **kwargs):
        rv = _v(request, *args, **kwargs)
        if isinstance(rv, http.HttpResponse):
            rv["Access-Control-Allow-Origin"] = "*"
            return rv
        response = http.HttpResponse(json.dumps(rv, indent=2),
                                     content_type="text/plain")
        response["Access-Control-Allow-Origin"] = "*"
        return response
    return _wrapped


@jsonify
def network(request):
    revs = request.GET.getlist("revision")
    if not revs:
        return http.HttpResponseBadRequest(
            "Need to pass at least one revision as query parameter"
            )
    branch_req = request.GET.get("branch", None)
    # support , and ' ' as separators, in addition to multiple revision params.
    allrevs = []
    parents = defaultdict(set)
    children = defaultdict(set)
    branches = set()
    for rev in revs:
        allrevs += re.split("[,\s]+", rev)
    changesets = set()
    for rev in allrevs:
        changesets.add(get_object_or_404(Changeset, revision__startswith=rev))
    # collect children
    change_objects = Changeset.objects
    change_parents = Changeset.parents.through.objects
    if branch_req is not None:
        branch_req = get_object_or_404(Branch, name=branch_req)
        change_objects = change_objects.filter(branch=branch_req)
        change_parents = \
                       change_parents.filter(to_changeset__branch=branch_req,
                                             from_changeset__branch=branch_req)
    down = 10
    newchanges = set(changesets)
    while down and newchanges:
        roots = set(newchanges)
        down -= 1
        cp = change_parents.filter(from_changeset__in=newchanges)
        new_ids = set()
        for pid, cid in cp.values_list('to_changeset_id', 'from_changeset_id'):
            if pid != 1:
                # exclude the global 12*'0' changeset
                new_ids.add(pid)
        newchanges = set(change_objects.filter(id__in=new_ids)) - changesets
        changesets |= newchanges
    found_children = set()
    newchanges = roots
    up = 20
    while up and newchanges:
        up -= 1
        cp = change_parents.filter(to_changeset__in=newchanges)
        new_ids = set()
        for pid, cid, bid in cp.values_list('to_changeset_id',
                                            'from_changeset_id',
                                            'to_changeset__branch_id'):
            parents[cid].add(pid)
            children[pid].add(cid)
            branches.add(bid)
            new_ids.add(cid)
        newchanges = set(change_objects.filter(id__in=new_ids))
        newchanges = newchanges - found_children
        changesets |= newchanges
        found_children |= newchanges

    parents = dict((k, tuple(v)) for k, v in parents.iteritems())
    children = dict((k, tuple(v)) for k, v in children.iteritems())
    changesets = sorted(changesets, key=lambda cs: cs.id)
    changeset_ids = map(lambda cs: cs.id, changesets)
    changesets = dict(map(lambda cs: (cs.id, {"id": cs.id,
                                 "revision": cs.revision,
                                 "branch_id": cs.branch_id,
                                 "description": cs.description,
                                 "user": cs.user,
                                 }),
                     changesets))
    repo_changesets = Repository.changesets.through.objects
    repo_changesets = repo_changesets.filter(changeset__in=changeset_ids)
    repos4change = defaultdict(list)
    repoids = set()
    for repoid, csid in repo_changesets.values_list('repository', 'changeset'):
        repos4change[csid].append(repoid)
        repoids.add(repoid)
    repos = Repository.objects.filter(id__in=repoids)
    repos = dict(repos.values_list('id', 'name'))

    class pushdict(dict):
        def __init__(self):
            dict.__init__(self)
            self['changes'] = []
    pushes = defaultdict(pushdict)
    pushes4change = defaultdict(list)
    push_changes = Push.changesets.through.objects
    push_changes = push_changes.filter(changeset__in=changeset_ids)
    push_changes = push_changes.filter(push__repository__in=repos.keys())
    for pushid, csid in push_changes.values_list('push_id', 'changeset_id'):
        pushes4change[csid].append(pushid)
        pushes[pushid]['changes'].append(csid)
    pushq = Push.objects.filter(id__in=pushes.keys())
    for push_d in pushq.values('id', 'repository', 'push_date', 'user'):
        push_d['push_date'] = push_d['push_date'].isoformat() + "Z"
        pushes[push_d['id']].update(push_d)
    branches = Branch.objects.filter(id__in=branches)
    branches = dict(branches.values_list('id', 'name'))
    return {'changesets': changesets,
            'roots': sorted(cs.id for cs in roots),
            'parents': parents,
            'children': children,
            'repositories': repos,
            'branches': branches,
            'repos4change': repos4change,
            'pushes': pushes,
            'pushes4change': pushes4change}


class ForkHierarchy(object):
    def __init__(self, baserepo):
        self.baserepo = baserepo
        self.tree = None  # result data
        self.forks = {}
        first_change = baserepo.changesets.filter(branch=1)[1]
        self.related = dict((repo.name, repo) for repo in
                            first_change.repositories.all())
        # heads cheats a bit, as we don't have closed branches in the db
        self.heads = {}
        for _name, _repo in self.related.iteritems():
            _c = _repo.changesets.order_by('-pk')
            self.heads[_name] = _c.filter(branch=1)[0]
        allrepos = self.related.values()
        allrepos.remove(baserepo)
        self.other_repos = sorted(allrepos,
                                  key=lambda r: -self.heads[r.name].id)

    def find_forks(self):
        forks = defaultdict(dict)
        for other in self.other_repos:
            fork_cs = self._get_fork_point(self.baserepo, other)
            if fork_cs is None:
                continue
            firstrepo = fork_cs.pushes.order_by('pk')[0].repository
            if firstrepo != self.baserepo:
                # baserepo is a clone of this, ignore
                continue
            setattr(fork_cs, 'firstrepo', firstrepo.name)
            forks[fork_cs][other] = None
        self.forks = forks

    def create_json(self):
        forks = sorted((t for t in self.forks.iteritems()),
                       key=lambda (cs, repos): cs.id)
        node = rv = {}
        for cs, repos in forks:
            children = [{
                "repo": repo.name,
                "revision": self.heads[repo.name].revision
                }
                        for repo in repos]
            node["repo"] = cs.firstrepo
            node["revision"] = cs.revision
            node["children"] = [{}] + children
            node = node["children"][0]
        node["repo"] = self.baserepo.name
        node["revision"] = self.heads[self.baserepo.name].revision
        return rv

    def _get_fork_point(self, one, other):
        # get changesets in the one repo ...
        forks = Changeset.objects.filter(repositories=one)
        # but not in the other repo ...
        forks = forks.exclude(repositories=other)
        # but that have a parent in the other
        forks = forks.filter(parents__repositories=other)
        forks = list(forks.values_list('id', flat=True))
        # get their parents
        forkpoints = Changeset.objects.filter(_children__in=forks)
        # and return the latest
        if forkpoints.exists():
            return forkpoints.order_by('-pk')[0]
        return None


@jsonify
def forks(self, name):
    repo = get_object_or_404(Repository, name=name)
    fh = ForkHierarchy(repo)
    fh.find_forks()
    return fh.create_json()
