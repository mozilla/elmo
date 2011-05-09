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
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
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

"""Views around Milestone data.
"""

from django.conf import settings
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import simplejson
from django.views.decorators.cache import cache_control

from collections import defaultdict
import re
import os.path

from life.models import Locale, Push, Changeset, Tree
from shipping.models import Milestone, Signoff, Milestone_Signoffs, Snapshot
from l10nstats.models import Run, Run_Revisions

from shipping.views import _signoffs


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

    mss = Milestone.objects.filter(id=ms.id)
    try:
        tree, forestname, foresturl = \
              mss.values_list('appver__tree__code','appver__tree__l10n__name',
                              'appver__tree__l10n__url')[0]
    except IndexError:
        tree, forestname, foresturl = \
              mss.values_list('appver__lasttree__code','appver__lasttree__l10n__name',
                              'appver__lasttree__l10n__url')[0]

    return render_to_response('shipping/about-milestone.html',
                              {'ms': ms,
                               'tree': tree,
                               'forestname': forestname,
                               'foresturl': foresturl,
                               },
                               context_instance=RequestContext(request))

def statuses(req, ms_code):
    """JSON work horse for the about() view.

    @see: about
    """
    try:
        ms = Milestone.objects.get(code=ms_code)
    except:
        return HttpResponse('no milestone found for %s' % ms_code)

    if ms.appver.tree is not None:
        tree = ms.appver.tree
    else:
        tree = ms.appver.lasttree

    sos_vals = _signoffs(ms).values_list('id','push__id', 'locale__code')
    sos = dict(d[:2] for d in sos_vals)
    loc2push = dict((d[2], d[1]) for d in sos_vals)
    locales = sorted(d[2] for d in sos_vals)
    allpushes = sos.values()

    def runs2dict(rs, prefix=''):
        fields = [prefix + f for f in ['locale__code']+Run.dfields]
        dcs = Run.to_class_string(runs.values(*fields), prefix)
        return dict((d[prefix+'locale__code'], {'class': cls, 'val': strval})
                    for d, cls, strval in dcs)

    # if the milestone is not shipped, let's check the active Runs, too
    active = {}
    if ms.status != 2:
        runs = Run.objects.filter(active__isnull=False)
        runs = runs.filter(tree=tree)
        active = runs2dict(runs)

    # if we have a previously shipped milestone, check the diffs
    previous = {}
    so_ids = dict((d[2], d[0]) for d in sos_vals) # current signoff ids
    pso = Milestone_Signoffs.objects.filter(milestone__id__lt=ms.id,
                                            milestone__appver__milestone=ms.id)
    pso = pso.order_by('milestone__id')
    for loc, sid, pid, mcode in pso.values_list('signoff__locale__code',
                                                'signoff__id',
                                                'signoff__push__id',
                                                'milestone__code'):
        previous[loc] = {'signoff': sid, 'push': pid, 'stone': mcode}
    # whatever is in so_ids but not in previous is added
    added = [loc for loc in so_ids.iterkeys() if loc not in previous]
    removed = [] # not yet used
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
    cs_ids = list(cs.values_list('id',flat=True))
    runs = Run_Revisions.objects.filter(changeset__id__in=cs_ids,
                                        run__tree=tree)
    latest = runs2dict(runs, 'run__')

    # get the snapshots from the sign-offs
    snaps = Snapshot.objects.filter(signoff__id__in=sos.keys(), test=0)
    runs = Run.objects.filter(id__in=list(snaps.values_list('tid',flat=True)))
    snapshots = runs2dict(runs)

    # get the shortrev's for all pushes, current sign-offs and previous
    pushes = Push.objects.annotate(tip=Max('changesets__id'))
    pushes = pushes.filter(id__in=allpushes)
    tips = dict(pushes.values_list('id', 'tip'))
    revmap = dict(Changeset.objects.filter(id__in=tips.values()).values_list('id', 'revision'))

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
            yield d

    return HttpResponse(simplejson.dumps({'items': list(items())}, indent=2),
                        mimetype="text/plain")


@cache_control(max_age=60)
def json_changesets(request):
    """Create a json l10n-changesets.
    This takes optional arguments of triples to link to files in repos
    specifying a special platform build. Used for multi-locale builds
    for fennec so far.
      multi_PLATFORM_repo: repository to load maemo-locales from
      multi_PLATFORM_rev: revision of file to load (default is usually fine)
      multi_PLATFORM_path: path inside the repo, say locales/maemo-locales

    XXX: For use in Firefox, this needs to learn about Japanese, still.
    """
    if request.GET.has_key('ms'):
        av_or_m = Milestone.objects.get(code=request.GET['ms'])
    elif request.GET.has_key('av'):
        av_or_m = AppVersion.objects.get(code=request.GET['av'])
    else:
        return HttpResponse('No milestone or appversion given')

    sos = _signoffs(av_or_m).annotate(tip=Max('push__changesets__id'))
    tips = dict(sos.values_list('locale__code', 'tip'))
    revmap = dict(Changeset.objects.filter(id__in=tips.values()).values_list('id', 'revision'))
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
    except:
        _ui = None
    if _ui is not None:
        for plat in sorted(multis.keys()):
            try:
                props = multis[plat]
                path = os.path.join(settings.REPOSITORY_BASE, props['repo'])
                repo = repository(_ui(), path)
                ctx = repo[props['rev']]
                fctx = ctx.filectx(props['path'])
                locales = fctx.data().split()
                for loc in locales:
                    extra_plats[loc].append(plat)
            except:
                pass

    tmpl = '''  "%(loc)s": {
    "revision": "%(rev)s",
    "platforms": ["%(plats)s"]
  }'''
    content = ('{\n' +
               ',\n'.join(tmpl % {'loc': l,
                                  'rev': revmap[tips[l]][:12],
                                  'plats': '", "'.join(platforms+extra_plats[l])
                                  }
                          for l in sorted(tips.keys())
                          ) +
               '\n}\n')
    r = HttpResponse(content,
                     content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=l10n-changesets.json'
    return r
