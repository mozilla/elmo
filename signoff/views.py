from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse 
from life.models import Locale, Push
from signoff.models import Milestone, Signoff, SignoffForm
from django import forms

import datetime

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
    while i < len(locales):
        locales[i].status = 'Open' if _getstatus(locales[i], mstone)[1] else 'Unmatched dependencies'
        
        current = Signoff.objects.filter(locale=locales[i], milestone=mstone).order_by('-pk')
        if current:
            locales[i].signoff = '[Signed off at %s by %s]' % (current[0].when.strftime("%Y-%m-%d %H:%M"), current[0].author)
        else:
            locales[i].signoff = ''
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
        mstones[i].status = 'Dependencies matches' if _getstatus(locale, mstones[i])[1] else 'Dependencies unmatched'
        if mstones[i].start_event.date < datetime.date.today() and \
            mstones[i].end_event.date > datetime.date.today():
            mstones[i].dates = 'Open till '+str(mstones[i].end_event.date)
        else:
            mstones[i].dates = str(mstones[i].start_event.date) + ' - ' + str(mstones[i].end_event.date)
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
        'status': 'open',
        'completeness': 1.0,
        'blockers': []
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

def signoff(request, loc=None, ms=None):
    locale = Locale.objects.get(code=loc)
    mstone = Milestone.objects.get(code=ms)
    error = ''
    (deps, enabled, timeslot) = _getstatus(locale, mstone)

    if request.method == 'POST' and enabled:
        instance = Signoff(milestone=mstone, locale=locale)
        form = SignoffForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
    else:
        current = Signoff.objects.filter(locale=locale, milestone=mstone).order_by('-pk')
        if current:
            current = current[0]
            form = SignoffForm({'push': current.push.id, 'author': current.author})
        else:
            form = SignoffForm()
    
    forest = mstone.appver.tree.l10n
    repo_url = forest.url+locale.code
    form.fields['push'].queryset = Push.objects.filter(repository__url=repo_url)
    
    if request.user.is_authenticated():
        form.fields['author'].initial = request.user

    if not enabled:
        for i in form.fields:
            form.fields[i].widget.attrs['disabled'] = 'disabled'
    
    return render_to_response('signoff/signoff.html', {
        'mstone': mstone,
        'locale': locale,
        'error': error,
        'form': form,
        'enabled': enabled,
        'dependencies': deps,
        'timeslot': timeslot,
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
