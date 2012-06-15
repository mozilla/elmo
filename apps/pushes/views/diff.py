# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""View for showing diffs between mercurial revisions.

The revisions don't necessarily need to be in the same repository, as long
as the repositories are related.
"""

from difflib import SequenceMatcher

from django.shortcuts import render
from django.conf import settings
from django import http
from django.views.generic.base import View

from life.models import Repository

from mercurial.ui import ui as _ui
from mercurial.hg import repository
from mercurial.copies import pathcopies
from mercurial.error import RepoLookupError

from Mozilla.Parser import getParser
from Mozilla.CompareLocales import AddRemove, Tree as DataTree



class DiffView(View):

    def _universal_newlines(self, content):
        "CompareLocales reads files with universal newlines, fake that"
        return content.replace('\r\n', '\n').replace('\r', '\n')

    def get(self, request):
        if not request.GET.get('repo'):
            return http.HttpResponseBadRequest("Missing 'repo' parameter")
        reponame = request.GET['repo']
        repopath = settings.REPOSITORY_BASE + '/' + reponame
        try:
            repo_url = Repository.objects.get(name=reponame).url
        except Repository.DoesNotExist:
            raise http.Http404("Repository not found")
        if not request.GET.get('from'):
            return http.HttpResponseBadRequest("Missing 'from' parameter")
        if not request.GET.get('to'):
            return http.HttpResponseBadRequest("Missing 'to' parameter")

        ui = _ui()
        repo = repository(ui, repopath)
        # Convert the 'from' and 'to' to strings (instead of unicode)
        # in case mercurial needs to look for the key in binary data.
        # This prevents UnicodeWarning messages.
        try:
            ctx1 = repo.changectx(str(request.GET['from']))
        except RepoLookupError:
            return http.HttpResponseBadRequest("Unrecognized 'from' parameter")
        try:
            ctx2 = repo.changectx(str(request.GET['to']))
        except RepoLookupError:
            return http.HttpResponseBadRequest("Unrecognized 'to' parameter")
        copies = pathcopies(ctx1, ctx2)
        match = None  # maybe get something from l10n.ini and cmdutil
        changed, added, removed = repo.status(ctx1, ctx2, match=match)[:3]

        # split up the copies info into thos that were renames and those that
        # were copied.
        moved = {}
        copied = {}
        for new_name, old_name in copies.items():
            if old_name in removed:
                moved[new_name] = old_name
            else:
                copied[new_name] = old_name

        paths = ([(f, 'changed') for f in changed]
                 + [(f, 'removed') for f in removed
                    if f not in moved.values()]
                 + [(f,
                     (f in moved and 'moved') or
                     (f in copied and 'copied')
                     or 'added') for f in added])
        diffs = DataTree(dict)
        for path, action in paths:
            lines = []
            try:
                p = getParser(path)
            except UserWarning:
                diffs[path].update({
                  'path': path,
                  'isFile': True,
                  'rev': ((action == 'removed') and request.GET['from']
                         or request.GET['to']),
                  'class': action,
                  'renamed': moved.get(path),
                  'copied': copied.get(path)
                })
                continue
            if action == 'added':
                a_entities = []
                a_map = {}
            else:
                realpath = (action == 'moved' and moved[path] or
                            action == 'copied' and copied[path] or
                            path)
                data = ctx1.filectx(realpath).data()
                data = self._universal_newlines(data)
                try:
                    p.readContents(data)
                    a_entities, a_map = p.parse()
                except:
                    # consider doing something like:
                    # logging.warn('Unable to parse %s', path, exc_info=True)
                    diffs[path].update({
                      'path': path,
                      'isFile': True,
                      'rev': ((action == 'removed') and request.GET['from']
                              or request.GET['to']),
                      'class': action,
                      'renamed': moved.get(path),
                      'copied': copied.get(path)
                    })
                    continue

            if action == 'removed':
                c_entities, c_map = [], {}
            else:
                data = ctx2.filectx(path).data()
                data = self._universal_newlines(data)
                try:
                    p.readContents(data)
                    c_entities, c_map = p.parse()
                except:
                    # consider doing something like:
                    # logging.warn('Unable to parse %s', path, exc_info=True)
                    diffs[path].update({
                      'path': path,
                      'isFile': True,
                      'rev': ((action == 'removed') and request.GET['from']
                             or request.GET['to']),
                      'class': action
                    })
                    continue
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
            container_class = lines and 'file' or 'empty-diff'
            diffs[path].update({'path': path,
                                'class': container_class,
                                'lines': lines,
                                'renamed': moved.get(path),
                                'copied': copied.get(path)
                                })
        diffs = diffs.toJSON().get('children', [])
        return render(request, 'pushes/diff.html', {
                        'given_title': request.GET.get('title', None),
                        'repo': reponame,
                        'repo_url': repo_url,
                        'old_rev': request.GET['from'],
                        'new_rev': request.GET['to'],
                        'diffs': diffs
                      })


diff = DiffView.as_view()
