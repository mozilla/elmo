from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse 
from life.models import Locale, Push
from signoff.models import Milestone, Signoff, SignoffForm
from django import forms
from django.core.urlresolvers import reverse
from django.db.models.query import QuerySet


import datetime

def _get_current_signoff(locale, mstone):
    current = Signoff.objects.filter(locale=locale, milestone=mstone).order_by('-pk')
    try:
        return current[0]
    except IndexError:
        return None

def index(request):
    locales = Locale.objects.all().order_by('code')
    mstones = Milestone.objects.all().order_by('code')
    
    i=0
    while i < len(mstones):
        if mstones[i].start_event.date < datetime.date.today() and \
            mstones[i].end_event.date > datetime.date.today():
            mstones[i].dates = 'Open till '+str(mstones[i].end_event.date)
        else:
            mstones[i].dates = str(mstones[i].start_event.date) + ' - ' + str(mstones[i].end_event.date)

        i+=1
    
    return render_to_response('signoff/index.html', {
        'locales': locales,
        'mstones': mstones,
    })

def locale_list(request, ms=None):
    locales = Locale.objects.all().order_by('code')
    error = None
    if ms:
        try:
            mstone = Milestone.objects.get(code=ms)
        except:
            mstone = None
            error = 'Could not find requested milestone'
    else:
        mstone = None
    
    i=0
    if  mstone:
        while i < len(locales):
            locales[i].params = []
            locales[i].params.append('Open' if _getstatus(locales[i], mstone)[1] else 'Unmatched dependencies')
            
            current = _get_current_signoff(locales[i], mstone)
            if current is not None:
                locales[i].params.append('Signed off at %s by %s' % (current.when.strftime("%Y-%m-%d %H:%M"), current.author))
            i+=1

    return render_to_response('signoff/locale_list.html', {
        'locales': locales,
        'mstone': mstone,
        'error': error,
    })

def milestone_list(request, loc=None):
    mstones = Milestone.objects.all().order_by('code')
    error = None
    if loc:
        try:
            locale = Locale.objects.get(code=loc)
        except:
            locale = None
            error = 'Could not find requested locale'
    else:
        locale = None
    i=0
    while i < len(mstones):
        mstones[i].params = []
        if mstones[i].start_event.date < datetime.date.today() and \
            mstones[i].end_event.date > datetime.date.today():
            mstones[i].params.append('Open till '+str(mstones[i].end_event.date))
        else:
            mstones[i].params.append(str(mstones[i].start_event.date) + ' - ' + str(mstones[i].end_event.date))

        if locale:
            mstones[i].params.append('Dependencies matches' if _getstatus(locale, mstones[i])[1] else 'Dependencies unmatched')
            current = _get_current_signoff(locale, mstones[i])
            if current:
                mstones[i].params.append('Signed off at %s by %s' % (current.when.strftime("%Y-%m-%d %H:%M"), current.author))

        i+=1
    return render_to_response('signoff/mstone_list.html', {
        'mstones': mstones,
        'locale': locale,
        'error': error,
    })

def _getstatus(locale, mstone):
    deps = []
    enabled = True
    deps.append({
        'name': 'Productization',
        'status': 'open', # 'open', 'pending', 'closed'
        'completeness': 1.0, # float 0.0 to 1.0
        'blockers': [] # blockers [('Desc', 'url'),('Desc', 'url')]
    })
    deps.append({
        'name': 'Web localization',
        'status': 'open',
        'completeness': 1.0,
        'blockers': []
    })

    if mstone.start_event.date < datetime.date.today() and \
        mstone.end_event.date > datetime.date.today():
        timeslot = 'open'
    else:
        timeslot = 'closed'
    
    i=0
    while i < len(deps):
        dep = deps[i]
        if dep['status'] == 'closed':
            dep['css'] = 'disabled'
            enabled = False
        elif dep['completeness'] < 0.5:
            dep['css'] = 'red'
            enabled = False
        elif dep['completeness'] < 0.9:
            dep['css'] = 'orange'
            enabled = False
        else:
            dep['css'] = 'green'
        dep['completeness'] = int(dep['completeness'] * 100)
        i+=1
    
    if enabled and timeslot == 'closed':
        enabled = False

    return (deps, enabled, timeslot)

def signoff(request, loc, ms):
    locale = Locale.objects.get(code=loc)
    mstone = Milestone.objects.get(code=ms)
    error = ''
    (deps, enabled, timeslot) = _getstatus(locale, mstone)

    if request.method == 'POST' and enabled:
        instance = Signoff(milestone=mstone, locale=locale)
        form = SignoffForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            request.session['signoff_note'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> added' % (mstone, locale, form.cleaned_data['author'])
            return HttpResponseRedirect(reverse('signoff.views.sublist', kwargs={'arg':loc, 'arg2':ms}))
    else:
        current = Signoff.objects.filter(locale=locale, milestone=mstone).order_by('-pk')
        if current:
            current = current[0]
            form = SignoffForm({'push': current.push.id, 'author': current.author})
        else:
            form = SignoffForm()
    
    forest = mstone.appver.tree.l10n
    repo_url = '%s%s/' % (forest.url, locale.code)
    q = Push.objects.filter(repository__url=repo_url).order_by('-push_date')[:10]
    print repo_url
    form.fields['push'].choices = [('','---')]+[(i.id, i) for i in q]
    
    if request.user.is_authenticated():
        form.fields['author'].initial = request.user

    if not enabled:
        for i in form.fields:
            form.fields[i].widget.attrs['disabled'] = 'disabled'
    
    note = request.session.get('signoff_note', None)
    if note:
        del request.session['signoff_note']
    
    return render_to_response('signoff/signoff.html', {
        'mstone': mstone,
        'locale': locale,
        'error': error,
        'form': form,
        'enabled': enabled,
        'dependencies': deps,
        'timeslot': timeslot,
        'note': note,
    })    

def signoff2(request, loc, ms):
    locale = Locale.objects.get(code=loc)
    mstone = Milestone.objects.get(code=ms)
    error = ''
    current = None
    (deps, enabled, timeslot) = _getstatus(locale, mstone)

    if request.method == 'POST' and enabled:
        instance = Signoff(milestone=mstone, locale=locale)
        form = SignoffForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            request.session['signoff_note'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> added' % (mstone, locale, form.cleaned_data['author'])
            return HttpResponseRedirect(reverse('signoff.views.sublist', kwargs={'arg':loc, 'arg2':ms}))
    else:
        current = Signoff.objects.filter(locale=locale, milestone=mstone).order_by('-pk')
        if current:
            current = current[0]
            form = SignoffForm({'push': current.push.id, 'author': current.author})
        else:
            current = None
            form = SignoffForm()
    
    forest = mstone.appver.tree.l10n
    repo_url = '%s%s/' % (forest.url, locale.code)
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
        if current and current.push.id is pushobj.id:
            cur = True
        else:
            cur = False
        pushes.append({'name': name,
                       'date': date,
                       'time': pushobj.push_date.strftime("%H:%M:%S"),
                       'object': pushobj,
                       'status': 'green',
                       'build': 'green',
                       'compare': 'green',
                       'colspan': 0,
                       'current': cur})
    if colspan > 0:
        pushes[len(pushes)-1-colspan]['colspan'] = colspan+1
    
    if request.user.is_authenticated():
        form.fields['author'].initial = request.user

    if not enabled:
        for i in form.fields:
            form.fields[i].widget.attrs['disabled'] = 'disabled'
    
    note = request.session.get('signoff_note', None)
    if note:
        del request.session['signoff_note']
    
    return render_to_response('signoff/signoff2.html', {
        'mstone': mstone,
        'locale': locale,
        'error': error,
        'form': form,
        'enabled': enabled,
        'dependencies': deps,
        'timeslot': timeslot,
        'note': note,
        'pushes': pushes,
        'current': current,
    }) 

def _code_type(code):
    if len(code)<4 or code.find('-')!=-1:
        return 'locale'
    else:
        return 'mstone'

def sublist(request, arg=None, arg2=None):
    if arg2:
        if _code_type(arg) == 'locale':
            return signoff2(request, loc=arg, ms=arg2)
        else:
            return signoff2(request, loc=arg2, ms=arg)
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
