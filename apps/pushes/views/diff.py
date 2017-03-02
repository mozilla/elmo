# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""View for showing diffs between mercurial revisions.

The revisions don't necessarily need to be in the same repository, as long
as the repositories are related.
"""
from __future__ import absolute_import

from difflib import SequenceMatcher
import logging

from django.shortcuts import render
from django.conf import settings
from django.db.models import Max
from django import http
from django.views.generic.base import View

from life.models import Repository, Changeset

from mercurial.ui import ui as _ui
from mercurial.hg import repository
from mercurial.copies import pathcopies, _chain  # HG INTERNAL
from mercurial.error import RepoLookupError

from compare_locales.parser import getParser
from compare_locales.compare import AddRemove, Tree as DataTree


class BadRevision(Exception):
    "Revision could not be resolved"
    pass


class DiffView(View):

    def _universal_newlines(self, content):
        "CompareLocales reads files with universal newlines, fake that"
        return content.replace('\r\n', '\n').replace('\r', '\n')

    def get(self, request):
        if not request.GET.get('repo'):
            return http.HttpResponseBadRequest("Missing 'repo' parameter")
        reponame = request.GET['repo']
        try:
            self.getrepo(reponame)
        except Repository.DoesNotExist:
            raise http.Http404("Repository not found")
        if not request.GET.get('from'):
            return http.HttpResponseBadRequest("Missing 'from' parameter")
        if not request.GET.get('to'):
            return http.HttpResponseBadRequest("Missing 'to' parameter")
        try:
            paths = self.contextsAndPaths(request.GET['from'],
                                          request.GET['to'])
        except BadRevision as e:
            return http.HttpResponseBadRequest(e.args[0])
        diffs = DataTree(dict)
        for path, action in paths:
            lines = self.diffLines(path, action)
            v = {'path': path,
                 'renamed': self.moved.get(path),
                 'copied': self.copied.get(path)}
            if lines is None:
                v.update({
                    'isFile': True,
                    'class': action,
                    'rev': ((action == 'removed') and request.GET['from']
                            or request.GET['to'])
                })
            else:
                container_class = lines and 'file' or 'empty-diff'
                v.update({
                    'class': container_class,
                    'lines': lines
                })
            diffs[path].update(v)
        diffs = diffs.toJSON().get('children', [])
        return render(request, 'pushes/diff.html', {
                        'given_title': request.GET.get('title', None),
                        'repo': reponame,
                        'repo_url': self.repo.url,
                        'old_rev': request.GET['from'],
                        'new_rev': request.GET['to'],
                        'diffs': diffs
                      })

    def getrepo(self, reponame):
        self.repo = Repository.objects.get(name=reponame)

    def contextsAndPaths(self, _from, _to):
        # if we get 'default' or 'tip' as revision, retrieve that
        # from the db, so that we don't rely on our local clones
        # having the same data as upstream for unified repos
        if _from in ('default', 'tip'):
            _from = (Changeset.objects
                     .filter(repositories=self.repo)
                     .filter(branch=1)  # default branch
                     .order_by('-pk')
                     .values_list('revision', flat=True)[0])
        if _to in ('default', 'tip'):
            _to = (Changeset.objects
                  .filter(repositories=self.repo)
                  .filter(branch=1)  # default branch
                  .order_by('-pk')
                  .values_list('revision', flat=True)[0])
        ui = _ui()
        repo = repository(ui, self.repo.local_path())
        # Convert the 'from' and 'to' to strings (instead of unicode)
        # in case mercurial needs to look for the key in binary data.
        # This prevents UnicodeWarning messages.
        try:
            self.ctx1, fromrepo, dbfrom = self.contextAndRepo(_from, repo)
        except RepoLookupError:
            raise BadRevision("Unrecognized 'from' parameter")
        try:
            self.ctx2, torepo, dbto = self.contextAndRepo(_to, repo)
        except RepoLookupError:
            raise BadRevision("Unrecognized 'to' parameter")
        if fromrepo == torepo:
            copies = pathcopies(self.ctx1, self.ctx2)
            match = None  # maybe get something from l10n.ini and cmdutil
            changed, added, removed = repo.status(self.ctx1, self.ctx2,
                                                  match=match)[:3]
        else:
            raise BadRevision("from and to parameter are not connected")

        # split up the copies info into thos that were renames and those that
        # were copied.
        self.moved = {}
        self.copied = {}
        for new_name, old_name in copies.items():
            if old_name in removed:
                self.moved[new_name] = old_name
            else:
                self.copied[new_name] = old_name

        paths = ([(f, 'changed') for f in changed]
                 + [(f, 'removed') for f in removed
                    if f not in self.moved.values()]
                 + [(f,
                     (f in self.moved and 'moved') or
                     (f in self.copied and 'copied')
                     or 'added') for f in added])
        return paths

    def contextAndRepo(self, rev, repo):
        '''Get a hg changectx for the given rev, preferably in the given repo.
        '''
        try:
            # Convert the 'from' and 'to' to strings (instead of unicode)
            # in case mercurial needs to look for the key in binary data.
            # This prevents UnicodeWarning messages.
            ctx = repo.changectx(str(rev))
            return ctx, repo, self.repo
        except RepoLookupError as e:
            # the favored repo doesn't have a changeset, look for an
            # active repo that does.
            try:
                dbrepo = (
                    Repository.objects
                    .filter(changesets__revision__startswith=rev)
                    .annotate(last_changeset=Max('changesets'))
                    .order_by('-last_changeset')
                    )[0]
            except IndexError:
                # can't find the changeset in other repos, raise the
                # original error
                raise e
        # ok, new repo
        otherrepo = repository(_ui(), dbrepo.local_path())
        return otherrepo.changectx(str(rev)), otherrepo, dbrepo

    def diffLines(self, path, action):
        lines = []
        try:
            p = getParser(path)
        except UserWarning:
            return None
        if action == 'added':
            a_entities = []
            a_map = {}
        else:
            realpath = (action == 'moved' and self.moved[path] or
                        action == 'copied' and self.copied[path] or
                        path)
            data = self.ctx1.filectx(realpath).data()
            data = self._universal_newlines(data)
            try:
                p.readContents(data)
                a_entities, a_map = p.parse()
            except:
                # consider doing something like:
                # logging.warn('Unable to parse %s', path, exc_info=True)
                return None

        if action == 'removed':
            c_entities, c_map = [], {}
        else:
            data = self.ctx2.filectx(path).data()
            data = self._universal_newlines(data)
            try:
                p.readContents(data)
                c_entities, c_map = p.parse()
            except:
                # consider doing something like:
                # logging.warn('Unable to parse %s', path, exc_info=True)
                return None
        a_list = sorted(a_map.keys())
        c_list = sorted(c_map.keys())
        ar = AddRemove()
        ar.set_left(a_list)
        ar.set_right(c_list)
        for action, item_or_pair in ar:
            if action == 'delete':
                lines.append({
                  'class': 'removed',
                  'oldval': [{'value': a_entities[a_map[item_or_pair]].val}],
                  'newval': '',
                  'entity': item_or_pair
                })
            elif action == 'add':
                lines.append({
                  'class': 'added',
                  'oldval': '',
                  'newval': [{'value': c_entities[c_map[item_or_pair]].val}],
                  'entity': item_or_pair
                })
            else:
                oldval = a_entities[a_map[item_or_pair[0]]].val
                newval = c_entities[c_map[item_or_pair[1]]].val
                if oldval == newval:
                    continue
                sm = SequenceMatcher(None, oldval, newval)
                oldhtml = []
                newhtml = []
                for op, o1, o2, n1, n2 in sm.get_opcodes():
                    if o1 != o2:
                        oldhtml.append({'class': op, 'value': oldval[o1:o2]})
                    if n1 != n2:
                        newhtml.append({'class': op, 'value': newval[n1:n2]})
                lines.append({'class': 'changed',
                              'oldval': oldhtml,
                              'newval': newhtml,
                              'entity': item_or_pair[0]})
        return lines
