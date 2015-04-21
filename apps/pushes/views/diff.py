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
                                          request.GET['to'],
                                          reponame)
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

    def contextsAndPaths(self, _from, _to, suggested_repo):
        repopath = settings.REPOSITORY_BASE + '/' + suggested_repo
        ui = _ui()
        repo = repository(ui, repopath)
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
            # find descent ancestor for ctx1 and ctx2
            try:
                anc_rev = (Changeset.objects
                           .exclude(id=1)  # exclude rev 0000
                           .filter(repositories=dbfrom)
                           .filter(repositories=dbto)
                           .filter(branch=1)
                           .order_by('-pk')
                           .values_list('revision', flat=True))[0]
                # mercurial doesn't like unicode
                anc_rev = str(anc_rev)
            except IndexError:
                raise BadRevision("from and to parameter are not connected")
            changed, added, removed, copies = \
                    self.processFork(fromrepo, self.ctx1, torepo, self.ctx2,
                                     anc_rev)
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
        repopath = settings.REPOSITORY_BASE + '/' + dbrepo.name
        otherrepo = repository(_ui(), repopath)
        return otherrepo.changectx(str(rev)), otherrepo, dbrepo

    def processFork(self, fromrepo, ctx1, torepo, ctx2, anc_rev):
        # piece together changed, removed, added, and copies
        match = None  # keep in sync with match above
        ctx3 = fromrepo.changectx(anc_rev)
        first_copies = pathcopies(ctx1, ctx3)
        changed, added, removed = fromrepo.status(ctx1, ctx3,
                                                  match=match)[:3]
        logging.debug('changed, added, removed, copies:\n %r %r %r %r',
                      changed, added, removed, first_copies)
        ctx3 = torepo.changectx(anc_rev)
        more_copies = pathcopies(ctx3, ctx2)
        more_reverse = dict((v, k) for k, v in more_copies.iteritems())
        more_changed, more_added, more_removed = torepo.status(ctx3, ctx2,
                                                               match=match)[:3]
        logging.debug('more_changed, added, removed, copies:\n %r %r %r %r',
                      more_changed, more_added, more_removed, more_copies)
        copies = _chain(ctx1, ctx2, first_copies, more_copies)  # HG INTERNAL
        # the second step removed a file, strip it from copies, changed
        # if it's in added, strip, otherwise add to removed
        check_manifests = set()  # moved back and forth, check manifests
        for f in more_removed:
            try:
                changed.remove(f)
            except ValueError:
                pass
            try:
                added.remove(f)
                # this file moved from ctx1 to ct2, adjust copies
                if (f in more_reverse and
                    f in first_copies):
                    if more_reverse[f] == first_copies[f]:
                        #file moving back and forth, check manifests below
                        check_manifests.add(first_copies[f])
            except ValueError:
                removed.append(f)
        # the second step added a file
        # strip it from removed, or add it to added
        for f in more_added:
            try:
                removed.remove(f)
            except ValueError:
                added.append(f)
        # see if a change was reverted, both changed,
        # manifests in to and from match
        m1 = m2 = None
        changed = set(changed)
        # only look at more_changed files we didn't add
        more_changed = set(more_changed) - set(added)
        both_changed = (changed & more_changed) | check_manifests
        # changed may be anything changed first, second, or both
        changed |= more_changed | check_manifests
        for tp in both_changed:
            fp = copies.get(tp, tp)
            if m1 is None:
                m1 = ctx1.manifest()
                m2 = ctx2.manifest()
            if m1[fp] == m2[tp]:
                changed.remove(tp)
        return (sorted(changed), sorted(set(added)), sorted(set(removed)),
                copies)

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
                  'oldval': [{'value':a_entities[a_map[item_or_pair]].val}],
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


diff = DiffView.as_view()
