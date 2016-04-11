# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views around Milestone data.
"""

from django.conf import settings
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import simplejson
from django.views.decorators.cache import cache_control

from collections import defaultdict
import re
import os.path

from life.models import Push, Changeset
from shipping.models import Milestone, Milestone_Signoffs, Snapshot
from l10nstats.models import Run, Run_Revisions

from shipping.views.status import SignoffDataView
from shipping.api import accepted_signoffs

from .utils import class_decorator


def about(request, ms_code):
    """View showing which locales are in which changeset on the given
    milestone. Also compare which are changed from the previously shipped
    milestone.

    Displays Run data for the sign-off snapshot, the latest for the signed-
    off push, and the latest. The latter only if the given milestone
    isn't shipped.

    The stati function in this module is the work horse delivering the
    json for this exhibit.
    """
    ms = get_object_or_404(Milestone, code=ms_code)

    forest = ms.appver.trees_over_time.latest().tree.l10n

    return render(request, 'shipping/about-milestone.html', {
                    'ms': ms,
                    'forestname': forest.name,
                    'foresturl': forest.url,
                    'Milestone': Milestone,
                  })


def statuses(req, ms_code):
    """JSON work horse for the about() view.

    @see: about
    """
    try:
        ms = Milestone.objects.get(code=ms_code)
    except:
        return HttpResponse('no milestone found for %s' % ms_code)

    tree = ms.appver.trees_over_time.latest().tree

    if ms.status == Milestone.SHIPPED:
        sos_vals = ms.signoffs.values_list('id', 'push__id', 'locale__code')
    else:
        sos_vals = (accepted_signoffs(ms.appver)
                    .values_list('id', 'push__id', 'locale__code'))
    sos = dict(d[:2] for d in sos_vals)
    loc2push = dict((d[2], d[1]) for d in sos_vals)
    locales = sorted(d[2] for d in sos_vals)
    allpushes = sos.values()

    def runs2dict(rs, prefix=''):
        fields = [prefix + f for f in ['locale__code'] + Run.dfields]
        dcs = Run.to_class_string(runs.values(*fields), prefix)
        return dict((d[prefix + 'locale__code'],
                     {'class': cls, 'val': strval})
                    for d, cls, strval in dcs)

    # if the milestone is not shipped, let's check the active Runs, too
    active = {}
    if ms.status != Milestone.SHIPPED:
        runs = Run.objects.filter(active__isnull=False)
        runs = runs.filter(tree=tree)
        active = runs2dict(runs)

    # if we have a previously shipped milestone, check the diffs
    previous = {}
    so_ids = dict((d[2], d[0]) for d in sos_vals)  # current signoff ids
    pso = Milestone_Signoffs.objects.filter(milestone__id__lt=ms.id,
                                            milestone__appver__milestone=ms.id)
    pso = pso.order_by('milestone__id')
    for loc, sid, pid, mcode in pso.values_list('signoff__locale__code',
                                                'signoff__id',
                                                'signoff__push__id',
                                                'milestone__code'):
        previous[loc] = {'signoff': sid, 'push': pid, 'stone': mcode}
    fallbacks = dict(ms.signoffs
        .exclude(appversion=ms.appver)
        .values_list('locale__code', 'appversion__code'))
    # whatever is in so_ids but not in previous is added
    added = [loc for loc in sorted(so_ids.iterkeys())
        if loc not in previous and loc not in fallbacks]
    removed = []  # not yet used
    # drop those from previous that we're shipping in the same rev
    for loc, details in previous.items():
        if loc in so_ids:
            if so_ids[loc] <= details['signoff']:
                previous.pop(loc)
        else:
            removed.append(loc)
    allpushes += [d['push'] for d in  previous.itervalues()]

    # get the most recent result for the signed off stamps
    cs = Changeset.objects.filter(pushes__id__in=sos.values())
    cs_ids = list(cs.values_list('id', flat=True))
    runs = Run_Revisions.objects.filter(changeset__id__in=cs_ids,
                                        run__tree=tree)
    latest = runs2dict(runs, 'run__')

    # get the snapshots from the sign-offs
    snaps = Snapshot.objects.filter(signoff__id__in=sos.keys(), test=0)
    runs = Run.objects.filter(id__in=list(snaps.values_list('tid', flat=True)))
    snapshots = runs2dict(runs)

    # get the shortrev's for all pushes, current sign-offs and previous
    pushes = Push.objects.annotate(tip=Max('changesets__id'))
    pushes = pushes.filter(id__in=allpushes)
    tips = dict(pushes.values_list('id', 'tip'))
    revmap = dict(Changeset.objects
                  .filter(id__in=tips.values())
                  .values_list('id', 'revision'))

    # generator to convert the various information to exhibit json
    def items():
        for loc in locales:
            d = {'label': loc, 'revision': revmap[tips[loc2push[loc]]][:12]}
            if loc in active:
                d['active'] = active[loc]['val']
                d['active_class'] = active[loc]['class']
            if loc in latest:
                d['latest'] = latest[loc]['val']
                d['latest_class'] = latest[loc]['class']
            if loc in snapshots:
                d['snapshot'] = snapshots[loc]['val']
                d['snapshot_class'] = snapshots[loc]['class']
            if loc in previous:
                d['updatedFromRev'] = revmap[tips[previous[loc]['push']]][:12]
                d['updatedFrom'] = previous[loc]['stone']
            elif loc in added:
                d['added'] = 'added'
            elif loc in fallbacks:
                d['fallback'] = fallbacks[loc]
            yield d

    return HttpResponse(simplejson.dumps({'items': list(items())}, indent=2),
                        mimetype="text/plain")


@class_decorator(cache_control(max_age=60))
class JSONChangesets(SignoffDataView):
    """Create a json l10n-changesets.
    This takes optional arguments of triples to link to files in repos
    specifying a special platform build. Used for multi-locale builds
    for fennec so far.
      multi_PLATFORM_repo: repository to load maemo-locales from
      multi_PLATFORM_rev: revision of file to load (default is usually fine)
      multi_PLATFORM_path: path inside the repo, say locales/maemo-locales

    XXX: For use in Firefox, this needs to learn about Japanese, still.
    """
    filename = 'l10n-changesets.json'

    def content(self, request, signoffs):
        sos = signoffs.annotate(tip=Max('push__changesets__id'))
        tips = dict(sos.values_list('locale__code', 'tip'))
        revmap = dict(Changeset.objects
                      .filter(id__in=tips.values())
                      .values_list('id', 'revision'))
        platforms = re.split('[ ,]+', request.GET['platforms'])
        multis = defaultdict(dict)
        for k, v in request.GET.iteritems():
            if not k.startswith('multi_'):
                continue
            plat, prop = k.split('_')[1:3]
            multis[plat][prop] = v
        extra_plats = defaultdict(list)
        try:
            from mercurial.hg import repository
            from mercurial.ui import ui as _ui
            _ui  # silence pyflakes
        except:
            _ui = None
        if _ui is not None:
            for plat in sorted(multis.keys()):
                try:
                    props = multis[plat]
                    path = os.path.join(settings.REPOSITORY_BASE,
                                        props['repo'])
                    repo = repository(_ui(), path)
                    ctx = repo[str(props['rev'])]
                    fctx = ctx.filectx(str(props['path']))
                    locales = fctx.data().split()
                    for loc in locales:
                        extra_plats[loc].append(plat)
                except:
                    pass

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

json_changesets = JSONChangesets.as_view()
