from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse 
from life.models import Locale, Push
from signoff.models import Milestone, Signoff, SignoffForm
from django import forms

def index(request):
    locales = Locale.objects.all().order_by('code')
    mstones = Milestone.objects.all().order_by('code')
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
    return render_to_response('signoff/mstone_list.html', {
        'mstones': mstones,
        'locale': locale,
        'error': error,
    })

def signoff(request, loc=None, ms=None):
    locale = Locale.objects.get(code=loc)
    mstone = Milestone.objects.get(code=ms)
    error = ''
    if request.method == 'POST':
        instance = Signoff(milestone=mstone, locale=locale)
        form = SignoffForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
    else:
        current = Signoff.objects.filter(locale=locale, milestone=mstone).order_by('-pk')
        if current:
            current = current[0]
            form = SignoffForm({'push': current.push.id})
        else:
            form = SignoffForm()
    
    forest = mstone.appver.tree.l10n
    repo_url = forest.url+locale.code
    form.fields['push'].queryset = Push.objects.filter(repository__url=repo_url)
    
    enabled = False
    
    return render_to_response('signoff/signoff.html', {
        'mstone': mstone,
        'locale': locale,
        'error': error,
        'form': form,
        'enabled': enabled,
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
