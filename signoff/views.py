from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse 
from life.models import Locale, Push, Tree
from signoff.models import Milestone, Signoff, SignoffForm, ActionForm
from l10nstats.models import Run
from django import forms
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django.core import serializers


from collections import defaultdict
import datetime

def index(request):
    locales = Locale.objects.all().order_by('code')
    mstones = Milestone.objects.all().order_by('code')

    for i in mstones:
        i.dates = _timeframe_desc(i)

    return render_to_response('signoff/index.html', {
        'locales': locales,
        'mstones': mstones,
    })

def milestone_list(request, loc=None):
    mstones = Milestone.objects.all().order_by('code')
    error = None
    locale = None
    if loc:
        try:
            locale = Locale.objects.get(code=loc)
        except:
            locale = None
            error = 'Could not find requested locale'

    for i in mstones:
        i.params = []
        i.params.append(_timeframe_desc(i))

        if locale:
            i.params.append('Dependencies matches' if i.status<2 else 'Dependencies unmatched')
            current = _get_current_signoff(locale, i)
            if current:
                i.params.append('Signed off at %s by %s' % (current.when, current.author))

    return render_to_response('signoff/mstone_list.html', {
        'mstones': mstones,
        'locale': locale,
        'error': error,
    })


def pushes(request):
    if request.GET['locale']:
        locale = Locale.objects.get(code=request.GET['locale'])
    if request.GET['ms']:
        mstone = Milestone.objects.get(code=request.GET['ms'])
    current = _get_current_signoff(locale, mstone)
    enabled = mstone.status<2
    user = request.user
    anonymous = user.is_anonymous()
    staff = user.is_staff
    if request.method == 'POST' and enabled: # we're going to process forms
        if anonymous: # ... but we're not logged in. Panic!
            request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s</span> could not be added - <strong>User not logged in</strong>' % (mstone, locale)
        else:
            if request.POST.has_key('accepted'): # we're in AcceptedForm mode
                if not staff: # ... but we have no privileges for that!
                    request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s</span> could not be accepted/rejected - <strong>User has not enough privileges</strong>' % (mstone, locale)
                else:
                    # hack around AcceptForm not taking strings, fixed in
                    # django 1.1
                    bval = {"True": 0, "False": 1}[request.POST['accepted']]
                    form = ActionForm({'signoff': current.id, 'flag': bval, 'author': user.id, 'comment': request.POST['comment']})
                    if form.is_valid():
                        form.save()
                        if request.POST['accepted'] == "False":
                            request.session['signoff_info'] = '<span style="font-style: italic">Rejected'
                        else:
                            request.session['signoff_info'] = '<span style="font-style: italic">Accepted'
                    else:
                        request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> could not be added' % (mstone, locale, user.username)
            else:
                instance = Signoff(appversion=mstone.appver, locale=locale, author=user)
                form = SignoffForm(request.POST, instance=instance)
                if form.is_valid():
                    form.save()
                    request.session['signoff_info'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> added' % (mstone, locale, user.username)
                else:
                    request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> could not be added' % (mstone, locale, user.username)
        return HttpResponseRedirect('%s?locale=%s&ms=%s' % (reverse('signoff.views.pushes'), locale.code ,mstone.code))

    form = SignoffForm()
    
    forest = mstone.appver.tree.l10n
    repo_url = '%s%s/' % (forest.url, locale.code)
    notes = _get_notes(request.session)
    curcol = {None:0,1:-1,0:1}[current.status] if current else 0
    try:
        accepted = Signoff.objects.filter(locale=locale, milestone=mstone, accepted=True).order_by('-pk')[0]
    except:
        accepted = None
    return render_to_response('signoff/pushes.html', {
        'mstone': mstone,
        'locale': locale,
        'form': form,
        'notes': notes,
        'current': current,
        'curcol': curcol,
        'accepted': accepted,
        'user': user.username,
        'pushes': simplejson.dumps(_get_api_items(locale, mstone, current)),
        'current_js': simplejson.dumps(_get_current_js(current)),
    })

def dashboard(request, ms):
    mstone = Milestone.objects.get(code=ms)
    tree = mstone.appver.tree
    args = ["tree=%s" % tree.code]
    return render_to_response('signoff/dashboard.html', {
            'mstone': mstone,
            'args': args,
            })

def l10n_changesets(request, milestone):
    sos = Signoff.objects.filter(milestone__code=milestone, accepted=True)
    sos = sos.order_by('locale__code', '-when')
    sos = sos.select_related('locale__code', 'push__changesets__tip')
    def createLines(q):
        lastLoc = None
        for so in q:
            if lastLoc == so.locale.code:
                # we already have an older signoff for this locale, skip
                continue
            lastLoc = so.locale.code
            yield "%s %s\n" % (so.locale.code, so.push.tip.shortrev)
    r = HttpResponse(createLines(sos), content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=l10n-changesets'
    return r

def shipped_locales(request, milestone):
    sos = Signoff.objects.filter(milestone__code=milestone, accepted=True)
    locales = list(sos.values_list('locale__code', flat=True).distinct()) + ['en-US']
    def withPlatforms(loc):
        if loc == 'ja':
            return 'ja linux win32\n'
        if loc == 'ja-JP-mac':
            return 'ja-JP-mac osx\n'
        return loc + '\n'
    
    r = HttpResponse(map(withPlatforms, sorted(locales)),
                      content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=shipped-locales'
    return r


def signoff_json(request):
    if request.GET['ms']:
        mso = Milestone.objects.get(code=request.GET['ms'])
    sos = Signoff.objects.filter(appversion__code=mso.appver.code)
    items = defaultdict(set)
    values = {True: 'accepted', False: 'rejected', None: 'pending'}
    for so in sos.select_related('locale'):
        items[so.locale.code].add(values[so.accepted])
    # make a list now
    items = [{"type": "SignOff", "label": locale, 'signoff': list(values)}
             for locale, values in items.iteritems()]
    return HttpResponse(simplejson.dumps({'items': items}, indent=2))

def pushes_json(request):
    loc = request.GET.get('locale', None)
    ms = request.GET.get('mstone', None)
    start = request.GET.get('start', 0)
    offset = request.GET.get('offset', 10)
    
    locale = None
    mstone = None
    current = None
    if loc:
        locale = Locale.objects.get(code=loc)
    if ms:
        mstone = Milestone.objects.get(code=ms)
    if loc and ms:
        cur = _get_current_signoff(locale, mstone)
    
    pushes = _get_api_items(locale, mstone, cur)
    return HttpResponse(simplejson.dumps({'pushes': pushes, 'current': _get_current_js(cur)}, indent=2))

#
#  Internal functions
#

def _get_current_signoff(locale, mstone):
    current = Signoff.objects.filter(locale=locale, appversion=mstone.appver).order_by('-pk')
    if not current:
        return None
    return current[0]

def _get_api_items(locale=None, mstone=None, current=None, offset=0, limit=10):
    if mstone:
        forest = mstone.appver.tree.l10n
        repo_url = '%s%s/' % (forest.url, locale.code) 
        pushobjs = Push.objects.filter(changesets__repository__url=repo_url).order_by('-push_date')[offset:offset+limit]
    else:
        pushobjs = Push.objects.order_by('-push_date')[offset:offset+limit]
    
    pushes = []
    for pushobj in pushobjs:
        if mstone:
            signoff_trees = [mstone.appver.tree]
        else:
            signoff_trees = Tree.objects.filter(l10n__repositories=pushobj.tip.repository, appversion__milestone__isnull=False)
        print signoff_trees
        name = '%s on [%s]' % (pushobj.user, pushobj.push_date)
        date = pushobj.push_date.strftime("%Y-%m-%d")
        cur = current and current.push.id == pushobj.id

        # check compare-locales
        runs2 = Run.objects.filter(revisions=pushobj.tip)
        for tree in signoff_trees:
            try:
                lastrun = runs2.filter(tree=tree).order_by('-build__id')[0]
                missing = lastrun.missing + lastrun.missingInFiles
                if missing:
                    compare = '%d missing' % missing
                elif lastrun.obsolete:
                    compare = '%d obsolete' % lastrun.obsolete
                else:
                    compare = 'green (%d%%)' % lastrun.completion
            except:
                compare = 'no build'

            pushes.append({'name': name,
                           'date': date,
                           'time': pushobj.push_date.strftime("%H:%M:%S"),
                           'id': pushobj.id,
                           'user': pushobj.user,
                           'revision': pushobj.tip.shortrev,
                           'revdesc': pushobj.tip.description,
                           'status': 'green',
                           'build': 'green',
                           'compare': compare,
                           'signoff': cur,
                           'url': '%spushloghtml?changeset=%s' % (pushobj.tip.repository.url, pushobj.tip.shortrev),
                           'accepted': current.accepted if cur else None})
    return pushes

def _get_current_js(cur):
    current = {}
    if cur:
        current['when'] = str(cur.when)
        current['author'] = str(cur.author)
        current['accepted'] = cur.accepted
    return current

def _get_notes(session):
    notes = {}
    for i in ('info','warning','error'):
        notes[i] = session.get('signoff_%s' % (i,), None)
        if notes[i]:
            del session['signoff_%s' % (i,)]
        else:
            del notes[i]
    return notes

def _timeframe_desc(i):
    if i.status<2:
        if i.end_event:
            return 'Open till '+str(i.end_event.date)
        else:
            return 'Open'
    else:
        if i.start_event and i.end_event:
            return '%s - %s' % (i.start_event.date, i.end_event.date)
        else:
            return 'Open'
