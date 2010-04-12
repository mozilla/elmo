from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.utils import simplejson

from life.models import Locale, Push, Changeset, Tree
from shipping.models import Milestone, Signoff, Snapshot, AppVersion, Action
from l10nstats.models import Run, Run_Revisions

from shipping.views import _signoffs


def about(req, ms_code):
    '''View showing which locales are in which changeset on the given
    milestone. Also compare which are changed from the previously shipped
    milestone.

    Displays Run data for the sign-off snapshot, the latest for the signed-
    off push, and the latest. The latter only if the given milestone
    isn't shipped.

    The stati function in this module is the work horse delivering the
    json for this exhibit.
    '''
    try:
        ms = Milestone.objects.get(code=ms_code)
    except:
        return HttpResponse('no milestone found for %s' % ms_code)

    # is there a previously shipped one?
    try:
        previous = Milestone.objects.filter(appver__milestone=ms,
                                            id__lt=ms.id,
                                            status=2)
        previous = previous.order_by('-pk')
        previous = previous[0].code
    except IndexError:
        previous = None

    mss = Milestone.objects.filter(id=ms.id)
    tree, forestname, foresturl = \
        mss.values_list('appver__tree__code','appver__tree__l10n__name',
                        'appver__tree__l10n__url')[0]

    return render_to_response('shipping/about-milestone.html',
                              {'ms': ms,
                               'tree': tree,
                               'forestname': forestname,
                               'foresturl': foresturl,
                               'previous': previous,
                               })

def stati(req, ms_code):
    '''JSON work horse for the about() view.

    @see: about
    '''
    try:
        ms = Milestone.objects.get(code=ms_code)
    except:
        return HttpResponse('no milestone found for %s' % ms_code)

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
        runs = runs.filter(tree__appversion__milestone=ms)
        active = runs2dict(runs)

    # if we have a previously shipped milestone, check the diffs
    previous = {}
    if 'previous' in req.GET:
        so_ids = dict((d[2], d[0]) for d in sos_vals)
        pso = Signoff.objects.filter(shipped_in__code=req.GET['previous'])
        for loc, id, pid in pso.values_list('locale__code', 'id', 'push__id'):
            if so_ids[loc] > id:
                previous[loc] = pid
                allpushes.append(pid)

    # get the most recent result for the signed off stamps
    cs = Changeset.objects.filter(pushes__id__in=sos.values())
    cs_ids = list(cs.values_list('id',flat=True))
    runs = Run_Revisions.objects.filter(changeset__id__in=cs_ids,
                                        run__tree__appversion__milestone=ms)
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
                d['updatedFrom'] = revmap[tips[previous[loc]]][:12]
            yield d

    return HttpResponse(simplejson.dumps({'items': list(items())}, indent=2),
                        mimetype="text/plain")
