from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse

def index(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('login')
    else:
        return profile(request)

def profile(request):
    return render_to_response('accounts/profile.html', {
        'user': request.user,
    })