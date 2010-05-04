from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import REDIRECT_FIELD_NAME
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.views.decorators import cache


@cache.cache_control(private=True)
def user_html(request):
    form = None
    if not request.user.is_authenticated():
        form = AuthenticationForm(request)
    return render_to_response('accounts/user.html',
                              {'form': form},
                              context_instance=RequestContext(request))


def logout(request, redirect_field_name=REDIRECT_FIELD_NAME):
    from django.contrib.auth import logout
    logout(request)
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    return HttpResponseRedirect(redirect_to or '/')
