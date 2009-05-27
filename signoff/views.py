from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse 
from life.models import Locale, Push, Tree
from signoff.models import Milestone, Signoff, SignoffForm, AcceptForm
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
        if _getstatus(i):
            i.dates = 'Open till '+str(i.end_event.date)
        else:
            i.dates = '%s - %s' % (i.start_event.date, i.end_event.date)
    
    return render_to_response('signoff/index.html', {
        'locales': locales,
        'mstones': mstones,
    })

def locale_list(request, ms=None):
    locales = Locale.objects.all().order_by('code')
    error = None
    mstone = None
    if ms:
        try:
            mstone = Milestone.objects.get(code=ms)
        except:
            mstone = None
            error = 'Could not find requested milestone'

    if  mstone:
        for i in locales:
            i.params = []
            i.params.append('Open' if _getstatus(mstone) else 'Unmatched dependencies')
            
            current = _get_current_signoff(i, mstone)
            if current is not None:
                i.params.append('Signed off at %s by %s' % (current.when, current.author))

    return render_to_response('signoff/locale_list.html', {
        'locales': locales,
        'mstone': mstone,
        'error': error,
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
        if _getstatus(i):
            i.params.append('Open till '+str(i.end_event.date))
        else:
            i.params.append('%s - %s' % (i.start_event.date, i.end_event.date))

        if locale:
            i.params.append('Dependencies matches' if _getstatus(i) else 'Dependencies unmatched')
            current = _get_current_signoff(locale, i)
            if current:
                i.params.append('Signed off at %s by %s' % (current.when, current.author))

    return render_to_response('signoff/mstone_list.html', {
        'mstones': mstones,
        'locale': locale,
        'error': error,
    })


def signoff(request, loc, ms):
    locale = Locale.objects.get(code=loc)
    mstone = Milestone.objects.get(code=ms)
    current = _get_current_signoff(locale, mstone)
    enabled = _getstatus(mstone)
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
                    bval = {"True": True, "False": False}[request.POST['accepted']]
                    form = AcceptForm({'accepted': bval}, instance=current)
                    if form.is_valid():
                        form.save()
                        if request.POST['accepted'] == "False":
                            request.session['signoff_info'] = '<span style="font-style: italic">Rejected'
                        else:
                            request.session['signoff_info'] = '<span style="font-style: italic">Accepted'
                    else:
                        request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> could not be added' % (mstone, locale, user.username)
            else:
                instance = Signoff(milestone=mstone, locale=locale, author=user)
                form = SignoffForm(request.POST, instance=instance)
                if form.is_valid():
                    form.save()
                    request.session['signoff_info'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> added' % (mstone, locale, user.username)
                else:
                    request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> could not be added' % (mstone, locale, user.username)
        return HttpResponseRedirect(reverse('signoff.views.sublist', kwargs={'arg':loc, 'arg2':ms}))

    form = SignoffForm()
    
    forest = mstone.appver.tree.l10n
    repo_url = '%s%s/' % (forest.url, locale.code)
    notes = _get_notes(request.session)
    curcol = {None:0,False:-1,True:1}[current.accepted] if current else 0
    try:
        accepted = Signoff.objects.filter(locale=locale, milestone=mstone, accepted=True).order_by('-pk')[0]
    except:
        accepted = None
    return render_to_response('signoff/signoff.html', {
        'mstone': mstone,
        'locale': locale,
        'form': form,
        'notes': notes,
        'current': current,
        'curcol': curcol,
        'accepted': accepted,
        'user': user.username,
    })

def dashboard(request, ms):
    mstone = Milestone.objects.get(code=ms)
    tree = mstone.appver.tree
    args = ["tree=%s" % tree.code]
    return render_to_response('signoff/dashboard.html', {
            'mstone': mstone,
            'args': args,
            })

def json(request, ms):
    sos = Signoff.objects.filter(milestone__code=ms)
    items = defaultdict(set)
    values = {True: 'accepted', False: 'rejected', None: 'pending'}
    for so in sos.select_related('locale'):
        items[so.locale.code].add(values[so.accepted])
    # make a list now
    items = [{"type": "SignOff", "label": locale, 'signoff': list(values)}
             for locale, values in items.iteritems()]
    return HttpResponse(simplejson.dumps({'items': items}, indent=2))

def _code_type(code):
    if len(code)<4 or code.find('-')!=-1:
        return 'locale'
    else:
        return 'mstone'

def sublist(request, arg=None, arg2=None):
    if arg2:
        if _code_type(arg) == 'locale':
            return signoff(request, loc=arg, ms=arg2)
        else:
            return signoff(request, loc=arg2, ms=arg)
    else:
        if _code_type(arg) == 'locale':
            return milestone_list(request, arg)
        else:
            return locale_list(request, arg)

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

def get_api_items(request):
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
        current = {}
        current['when'] = str(cur.when)
        current['author'] = str(cur.author)
    
    
    pushes = _get_api_items(locale, mstone, cur)
    return HttpResponse(simplejson.dumps({'pushes': pushes, 'current': current}, indent=2))


def dstest(request):
    import xmlrpclib
    bzilla = xmlrpclib.ServerProxy("https://bugzilla.mozilla.org/xmlrpc.cgi")
    print bzilla.Bug.get_bugs({'ids':[6323], 'permissive': 1})

    return render_to_response('signoff/dstest.html', {
        'mstone': 1,
    }) 

#
#  Internal functions
#

def _get_current_signoff(locale, mstone):
    current = Signoff.objects.filter(locale=locale, milestone=mstone).order_by('-pk')
    if not current:
        return None
    #current[0].when = current[0].when.strftime("%Y-%m-%d %H:%M")
    return current[0]

def _getstatus(mstone):
    today = datetime.date.today()
    return mstone.start_event.date <= today and mstone.end_event.date >= today

def _get_api_items(locale=None, mstone=None, current=None, offset=0, limit=10):
    if mstone:
        forest = mstone.appver.tree.l10n
        repo_url = '%s%s/' % (forest.url, locale.code) 
        pushobjs = Push.objects.filter(repository__url=repo_url).order_by('-push_date')[offset:offset+limit]
    else:
        pushobjs = Push.objects.order_by('-push_date')[offset:offset+limit]
    
    pushes = []
    for pushobj in pushobjs:
        if mstone:
            signoff_trees = [mstone.appver.tree]
        else:
            signoff_trees = Tree.objects.filter(l10n__repositories=pushobj.repository, appversion__milestone__isnull=False)
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
                           #'object': pushobj,
                           'id': pushobj.id,
                           'user': pushobj.user,
                           'revision': pushobj.tip.shortrev,
                           'revdesc': pushobj.tip.description,
                           'status': 'green',
                           'build': 'green',
                           'compare': compare,
                           'signoff': cur,
                           'url': '%spushloghtml?changeset=%s' % (pushobj.repository.url, pushobj.tip.shortrev),
                           'accepted': current.accepted if cur else None})
    return pushes

def _get_notes(session):
    notes = {}
    for i in ('info','warning','error'):
        notes[i] = session.get('signoff_%s' % (i,), None)
        if notes[i]:
            del session['signoff_%s' % (i,)]
        else:
            del notes[i]
    return notes
