from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse 
from life.models import Locale, Push
from signoff.models import Milestone, Signoff, SignoffForm, AcceptForm
from django import forms
from django.core.urlresolvers import reverse

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
                i.params.append('Signed off at %s by %s' % (current.when.strftime("%Y-%m-%d %H:%M"), current.author))

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
                i.params.append('Signed off at %s by %s' % (current.when.strftime("%Y-%m-%d %H:%M"), current.author))

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
                    form = AcceptForm(request.POST, instance=current)
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
    pushes = _get_pushes(repo_url, current)
    notes = _get_notes(request.session)
    curcol = {None:0,False:-1,True:1}[current.accepted] if current else 0
    try:
        accepted = Signoff.objects.filter(locale=locale, milestone=mstone, accepted=True).order_by('-pk')[0].get()
    except:
        accepted = None
    return render_to_response('signoff/signoff.html', {
        'mstone': mstone,
        'locale': locale,
        'form': form,
        'notes': notes,
        'pushes': pushes,
        'current': current,
        'curcol': curcol,
        'accepted': accepted,
        'user': user.username,
    }) 

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
    sos = Signoff.objects.filter(milestone__code=milestone)
    sos = sos.order_by('locale__code')
    r = HttpResponse(("%s %s\n" % (so.locale.code, so.push.tip.shortrev)
                      for so in sos),
                      content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=l10n-changesets'
    return r

def shipped_locales(request, milestone):
    sos = Signoff.objects.filter(milestone__code=milestone)
    locales = list(sos.values_list('locale__code', flat=True)) + ['en-US']
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
    try:
        return current[0]
    except IndexError:
        return None

def _getstatus(mstone):
    today = datetime.date.today()
    return mstone.start_event.date < today and mstone.end_event.date > today

def _get_pushes(repo_url, current):
    pushobjs = Push.objects.filter(repository__url=repo_url).order_by('-push_date')[:10]
    
    pushes = []
    prev_date = None
    colspan = 0
    for pushobj in pushobjs:
        name = '%s on [%s]' % (pushobj.user, pushobj.push_date)
        date = pushobj.push_date.strftime("%Y-%m-%d")
        if date == prev_date:
            date = None
            colspan += 1
        else:
            if colspan > 0:
                pushes[len(pushes)-1-colspan]['colspan'] = colspan+1
                colspan = 0
            prev_date = pushobj.push_date.strftime("%Y-%m-%d")
        cur = current and current.push.id is pushobj.id

        pushes.append({'name': name,
                       'date': date,
                       'time': pushobj.push_date.strftime("%H:%M:%S"),
                       'object': pushobj,
                       'status': 'green',
                       'build': 'green',
                       'compare': 'green',
                       'colspan': 0,
                       'current': cur,
                       'accepted': current.accepted if cur else None})
    if colspan > 0:
        pushes[len(pushes)-1-colspan]['colspan'] = colspan+1
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
