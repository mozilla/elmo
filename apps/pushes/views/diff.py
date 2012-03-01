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

"""View for showing diffs between mercurial revisions.

The revisions don't necessarily need to be in the same repository, as long
as the repositories are related.
"""

from difflib import SequenceMatcher

from django.shortcuts import render
from django.conf import settings
from django import http

from life.models import Repository

from mercurial.ui import ui as _ui
from mercurial.hg import repository
from mercurial.copies import pathcopies

from Mozilla.Parser import getParser
from Mozilla.CompareLocales import AddRemove, Tree as DataTree


def _universal_newlines(content):
    "CompareLocales reads files with universal newlines, fake that"
    return content.replace('\r\n', '\n').replace('\r', '\n')


def diff(request):
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
    ctx1 = repo.changectx(str(request.GET['from']))
    ctx2 = repo.changectx(str(request.GET['to']))
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
            data = _universal_newlines(data)
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
            data = _universal_newlines(data)
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
    return render(request, 'shipping/diff.html', {
                    'given_title': request.GET.get('title', None),
                    'repo': reponame,
                    'repo_url': repo_url,
                    'old_rev': request.GET['from'],
                    'new_rev': request.GET['to'],
                    'diffs': diffs
                  })
