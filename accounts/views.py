from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse

def index(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('login')
    else:
        return profile(request)

def profile(request):
    staff = 'drivers' in request.user.groups.values_list('name', flat=True)
    return render_to_response('accounts/profile.html', {
        'user': request.user,
        'staff': staff,
    })