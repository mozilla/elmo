# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for shipping metrics.
'''
from __future__ import absolute_import
from collections import defaultdict
import os
import re

from django.http import HttpResponse, HttpResponseBadRequest
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.views.generic import View
from life.models import Changeset, Locale, Push
from l10nstats.models import Run, ProgressPosition
from shipping.api import accepted_signoffs, flags4appversions
from shipping.models import Action, Signoff, AppVersion
from django.views.decorators.cache import cache_control
import json
from django.db.models import Max

from .utils import class_decorator
from shipping.forms import SignoffFilterForm


class BadRequestData(Exception):
    pass


class SignoffDataView(View):
    """Base view to reuse code to handle av= query params.

    First pass is process_request, which sets self.av.
    Overload this method to handle further args.
    Second pass is get_data, which gets
    - a appversion, and calls data_for_appversion.
    actual content creation step, content(), which returns a string or
    These tuples are then used by the
    iterator of strings, to be passed into the response.
    """
    filename = None

    def process_request(self, request, *args, **kwargs):
        form = SignoffFilterForm(request.GET)
        if form.is_valid():
            self.appver = form.cleaned_data['av']
            self.up_until = form.cleaned_data['up_until']
        else:
            raise BadRequestData(form.errors.items())

    def get_data(self):
        if self.appver:
            appver = self.appver
        else:
            raise RuntimeError("Need appversion")
        return self.data_for_appversion(appver)

    def data_for_appversion(self, appver):
        return (accepted_signoffs(appver, up_until=self.up_until),)

    def get(self, request, *args, **kwargs):
        try:
            self.process_request(request)
        except BadRequestData as msg:
            return HttpResponseBadRequest(msg)
        try:
            data = self.get_data()
        except RuntimeError as msg:
            return HttpResponseBadRequest(str(msg))
        content = self.content(request, *data)
        r = HttpResponse(content, content_type='text/plain; charset=utf-8')
        if self.filename:
            r['Content-Disposition'] = 'inline; filename="%s"' % self.filename
        r['Access-Control-Allow-Origin'] = '*'
        return r


@class_decorator(cache_control(max_age=60))
class Changesets(SignoffDataView):
    filename = 'l10n-changesets'

    def content(self, request, signoffs):
        sos = signoffs.annotate(tip=Max('push__changesets__id'))
        tips = dict(sos.values_list('locale__code', 'tip'))
        revs = Changeset.objects.filter(id__in=tips.values())
        revmap = dict(revs.values_list('id', 'revision'))
        return ['%s %s\n' % (l, revmap[tips[l]][:12])
                for l in sorted(tips.keys())]


@class_decorator(cache_control(max_age=60))
class JSONChangesets(SignoffDataView):
    """Create a json l10n-changesets.
    This takes optional arguments of triples to link to files in repos
    specifying a special platform build. Used for multi-locale builds
    for fennec so far.
      multi_PLATFORM_repo: repository to load maemo-locales from
      multi_PLATFORM_rev: revision of file to load (default is usually fine)
      multi_PLATFORM_path: path inside the repo, say locales/maemo-locales
    """
    filename = 'l10n-changesets.json'

    def content(self, request, signoffs):
        sos = signoffs.annotate(tip=Max('push__changesets__id'))
        tips = dict(sos.values_list('locale__code', 'tip'))
        revmap = dict(Changeset.objects
                      .filter(id__in=tips.values())
                      .values_list('id', 'revision'))
        platforms = re.split('[ ,]+', request.GET.get('platforms', ''))
        multis = defaultdict(dict)
        for k, v in request.GET.iteritems():
            if not k.startswith('multi_'):
                continue
            plat, prop = k.split('_')[1:3]
            multis[plat][prop] = v
        extra_plats = defaultdict(list)
        import hglib
        for plat in sorted(multis.keys()):
            props = multis[plat]
            path = os.path.join(settings.REPOSITORY_BASE,
                                props['repo'])
            try:
                repo = hglib.open(path)
            except:
                raise SuspiciousOperation("Repo %s doesn't exist" %
                                          str(props['repo']))
            try:
                rev = str(props['rev'])
                if rev in ('default', 'tip'):
                    # let's not rely on the repo to have this right
                    rev = (Changeset.objects
                           .filter(repositories__name=props['repo'])
                           .filter(branch=1)  # default branch
                           .order_by('-pk')
                           .values_list('revision', flat=True)[0])
                locales = repo.cat(files=['path:'+str(props['path'])],
                                   rev=rev).split()
            finally:
                repo.close()
            for loc in locales:
                extra_plats[loc].append(plat)

        tmpl = '''  "%(loc)s": {
    "revision": "%(rev)s",
    "platforms": ["%(plats)s"]
  }'''
        content = [
          '{\n',
          ',\n'.join(tmpl % {'loc': l,
                             'rev': revmap[tips[l]][:12],
                             'plats': '", "'.join(platforms + extra_plats[l])}
                              for l in sorted(tips.keys())
                              ),
          '\n}\n'
        ]
        content = ''.join(content)
        return content


@class_decorator(cache_control(max_age=60))
class ShippedLocales(SignoffDataView):
    filename = 'shipped-locales'

    def content(self, request, signoffs):
        sos = signoffs.values_list('locale__code', flat=True)
        locales = list(sos) + ['en-US']

        def withPlatforms(loc):
            if loc == 'ja':
                return 'ja linux win32\n'
            if loc == 'ja-JP-mac':
                return 'ja-JP-mac osx\n'
            return loc + '\n'

        return map(withPlatforms, sorted(locales))


@class_decorator(cache_control(max_age=60))
class StatusJSON(SignoffDataView):

    EXHIBIT_SCHEMA = {
    "types": {
        "Build": {
            "pluralLabel": "Builds"
            },
        "Priority": {
            "pluralLabel": "Priorities"
            }
        },
    "properties": {
        "completion": {
            "valueType": "number"
            },
        "changed": {
            "valueType": "number"
            },
        "missing": {
            "valueType": "number"
            },
        "report": {
            "valueType": "number"
            },
        "warnings": {
            "valueType": "number"
            },
        "errors": {
            "valueType": "number"
            },
        "obsolete": {
            "valueType": "number"
            },
        "unchanged": {
            "valueType": "number"
            },
        "starttime": {
            "valueType": "date"
            },
        "endtime": {
            "valueType": "date"
            }
        }
    }

    def process_request(self, request, *args, **kwargs):
        """Get hold of potential locale argument"""
        self.locales = request.GET.getlist('locale')
        self.trees = request.GET.getlist('tree')
        self.avs = request.GET.getlist('av')

        if self.avs:
            # make sure its tree is in self.trees
            trees = (AppVersion.trees.through.objects
                     .current()
                .filter(appversion__code__in=self.avs)
                .values_list('tree__code', flat=True))
            for tree in trees:
                if tree not in self.trees:
                    self.trees.append(tree)

        if self.trees:
            # make sure its appversion is in self.avs
            avs = (AppVersion.trees.through.objects
                   .current()
                .filter(tree__code__in=self.trees)
                .values_list('appversion__code', flat=True))
            for av in avs:
                if av not in self.avs:
                    self.avs.append(av)

    def get_data(self):
        runs = self.get_runs()
        signoffs = self.get_signoffs()
        return (runs + signoffs,)

    def get_runs(self):
        q = (Run.objects.filter(active__isnull=False)
                        .order_by('tree__code', 'locale__code'))
        posq = ProgressPosition.objects.all()
        if self.trees:
            q = q.filter(tree__code__in=self.trees)
            posq = posq.filter(tree__code__in=self.trees)
        if self.locales:
            q = q.filter(locale__code__in=self.locales)
            posq = posq.filter(locale__code__in=self.locales)
        prog_pos_items = [
            {
                'label': '%s/%s' % (pp.tree.code, pp.locale.code),
                'type': 'Progress',
                'background_offset_x': pp.x,
                'background_offset_y': pp.y
            } for pp in posq.select_related('tree', 'locale')]
        leafs = ['tree__code', 'locale__code', 'id',
                 'missing', 'missingInFiles', 'report', 'warnings',
                 'errors', 'unchanged', 'total', 'obsolete', 'changed',
                 'completion']

        def toExhibit(d):
            missing = d['missing'] + d['missingInFiles']
            result = 'success'
            tree = d['tree__code']
            locale = d['locale__code']
            if ('errors' in d and d['errors']):
                result = 'error'
            elif missing:
                result = 'failure'
            elif d['obsolete']:
                result = 'warnings'

            rd = {'id': '%s/%s' % (tree, locale),
                  'runid': d['id'],
                  'label': locale,
                  'locale': locale,
                  'tree': tree,
                  'type': 'Build',
                  'result': result,
                  'missing': missing,
                  'report': d['report'],
                  'warnings': d['warnings'],
                  'changed': d['changed'],
                  'unchanged': d['unchanged'],
                  'total': d['total'],
                  'completion': d['completion']
                  }
            if 'errors' in d and d['errors']:
                rd['errors'] = d['errors']
            if 'obsolete' in d and d['obsolete']:
                rd['obsolete'] = d['obsolete']
            return rd
        run_items = map(toExhibit, q.values(*leafs))
        self.runids2tree = dict((d['runid'], d['tree']) for d in run_items)
        return prog_pos_items + run_items

    def get_signoffs(self):
        appversions_with_pushes = []
        _treeid_to_avt = {}
        tree_ids = {}
        avts = (AppVersion.trees.through.objects
            .current()
            .filter(appversion__accepts_signoffs=True)
        )
        if self.avs:
            avts = avts.filter(appversion__code__in=self.avs)
        for avt in avts.select_related('appversion__app', 'tree__l10n'):
            _treeid_to_avt[avt.tree.id] = avt
            tree_ids[avt.tree.code] = avt.tree.id

        appvers = [avt.appversion for avt in _treeid_to_avt.values()]
        locales = None
        if self.locales:
            locales = list(Locale.objects
                .filter(code__in=self.locales)
                .values_list('id', flat=True))

        locflags4av = flags4appversions(appvers, locales=locales)
        av2tree = dict((avt.appversion.code, avt.tree.code)
            for avt in _treeid_to_avt.itervalues())
        values = dict(Action._meta.get_field('flag').flatchoices)
        so_items = {}
        actions = {}
        for av in appvers:
            for loc, (real_av, flags) in locflags4av[av].iteritems():
                flag_values = [
                    (real_av == av.code or f != Action.ACCEPTED) and values[f]
                    or real_av
                    for f in flags]
                item = {
                    'flags': flag_values,
                    'state': None,
                    'action': []
                }
                if Action.ACCEPTED in flags:
                    item['state'] = (real_av == av.code) and 'OK' or real_av
                if Action.REJECTED in flags:
                    item['action'].append('rejected')
                if Action.PENDING in flags:
                    item['action'].append('review')
                so_items[(av2tree[av.code], loc)] = item
                for flag, action in flags.items():
                    # don't keep track of fallback actions
                    if not (real_av != av.code and flag == Action.ACCEPTED):
                        actions[action] = [av, loc]
        for action, signoff, push_date in (Action.objects
            .filter(id__in = actions.keys())
            .values_list('id', 'signoff', 'signoff__push__push_date')):
                actions[action] += [signoff, push_date]
        last_action = {}
        last_signoff = {}
        for action, (av, loc, signoff, push_date) in sorted(
                actions.iteritems(),
                key=lambda t: t[1][3],
                reverse=True):
            if (av, loc) in last_action:
                continue
            last_action[(av, loc)] = push_date
            last_signoff[(av, loc)] = signoff

        runs_with_open_av = [run for run, tree in self.runids2tree.items()
            if tree in tree_ids and _treeid_to_avt[tree_ids[tree]].appversion.accepts_signoffs]
        changesets = dict((tuple(t[:2]), t[2])
            for t in Run.revisions.through.objects
            .filter(run__in=runs_with_open_av,
                    changeset__repositories__locale__isnull=False)
            .values_list('run__tree', 'run__locale__code', 'changeset'))
        pushdates = dict((tuple(t[:2]), t[2])
            for t in Push.changesets.through.objects
            .filter(changeset__in=set(changesets.values()))
            .values_list('changeset', 'push__repository__forest', 'push__push_date'))
        avl_has_new_run = set()
        maybe_new_run = []
        for (treeid, locale_code), changeset in changesets.iteritems():
            avt = _treeid_to_avt[treeid]
            push_date = pushdates[(changeset, avt.tree.l10n.id)]
            if avt.start and push_date < avt.start:
                # need update
                appversions_with_pushes.append({
                    "needs_update": True,
                    "type": "NewPush",
                    "label": avt.tree.code  + '/' + locale_code
                })
                continue
            if avt.end and push_date > avt.end:
                continue
            if ((avt.appversion, locale_code) in last_action and
                last_action[(avt.appversion, locale_code)] >= push_date):
                    continue
            maybe_new_run.append((avt.appversion, changeset, avt.tree.code,
                locale_code, last_signoff.get((avt.appversion, locale_code))
            ))

        # find out if the sign-off is on the same revision as the last push
        old_signoffs = filter(None, (t[4] for t in maybe_new_run))
        signoffs_to_skip = set()
        if old_signoffs:
            so_tips = dict(Signoff.objects
                .filter(id__in=old_signoffs)
                .annotate(cs=Max("push__changesets"))
                .values_list('id', 'cs'))
            latest_changeset = dict((t[4], t[1]) for t in maybe_new_run)
            for so_id, tip in so_tips.iteritems():
                if latest_changeset[so_id] == tip:
                    signoffs_to_skip.add(so_id)
        for av, changeset, tree_code, locale_code, last_so in maybe_new_run:
            if last_so in signoffs_to_skip:
                continue
            avl_has_new_run.add((tree_code, locale_code))
            appversions_with_pushes.append({
                "new_run": "sign off",
                "type": "NewPush",
                "label": tree_code + '/' + locale_code
            })

        # make a list now
        items = []
        for (tree, locale), values in sorted(so_items.iteritems(),
                                             key=lambda t:t[0]):
            glyph = ''
            if values['state'] == 'OK':
                glyph = 'check'
                if (tree, locale) in avl_has_new_run:
                    glyph = 'graph'
            elif values['state']:
                glyph = 'warning'
            item = {
                "type": "SignOff",
                "label": "%s/%s" % (tree, locale),
                "tree": tree,
                "state": values['state'],
                "state_glyph": glyph,
                "signoff": sorted(values['flags'])
            }
            if values['action']:
                item['action'] = values['action']
            items.append(item)

        items += [{"type": "AppVer4Tree",
                   "label": tree,
                   "appversion": av}
                  for av, tree in av2tree.iteritems()]
        items += appversions_with_pushes
        return items

    def content(self, request, items):
        data = self.EXHIBIT_SCHEMA.copy()
        data['items'] = items
        return json.dumps(data, indent=2)
