from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse 
from life.models import Locale
from signoff.models import Milestone

def index(request):
    return render_to_response('signoff/index.html')

def locale_list(request):
    locales = Locale.objects.all().order_by('code')
    return render_to_response('signoff/locale_list.html', {
        'locales': locales
    })

def milestone_list(request):
    mstones = Milestone.objects.all().order_by('code')
    return render_to_response('signoff/mstone_list.html', {
        'mstones': mstones
    })

def locale(request, code):
    return HttpResponse(code)

def sublist(request, arg):
    if len(arg)<4 or arg.find('-')!=-1:
        return milestone_list(request)
    else:
        return locale_list(request)
