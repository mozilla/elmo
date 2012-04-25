# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for logging in and out of l10n_site.
'''


from django.contrib.auth.views import REDIRECT_FIELD_NAME
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators import cache
from django.core.context_processors import csrf
from django.utils import simplejson as json
from django.contrib.auth.views import login as django_login
from forms import AuthenticationForm
from lib.auth.backends import AUTHENTICATION_SERVER_ERRORS


class HttpResponseServiceUnavailableError(HttpResponse):
    """
        503 Service Unavailable
        The server is currently unavailable (because it is overloaded or down
        for maintenance). Generally, this is a temporary state.
    """
    status_code = 503

    def __init__(self, *args, **kwargs):
        kwargs['content'] = 'Service Unavailable'
        super(HttpResponseServiceUnavailableError, self
              ).__init__(*args, **kwargs)


def login(request):
    # the template is only used to show errors
    try:
        response = django_login(
          request,
          template_name='accounts/login_form.html',
          authentication_form=AuthenticationForm,
        )
    except AUTHENTICATION_SERVER_ERRORS:
        return HttpResponseServiceUnavailableError()

    if request.is_ajax():
        if response.status_code == 302:
            # it worked!
            return user_json(request)

    return response


@cache.cache_control(private=True)
def user_json(request):
    result = {}
    if request.user.is_authenticated():
        if request.user.first_name:
            result['user_name'] = request.user.first_name
        else:
            result['user_name'] = request.user.username
    else:
        result['csrf_token'] = unicode(csrf(request)['csrf_token'])
    return HttpResponse(json.dumps(result), mimetype="application/json")


def logout(request, redirect_field_name=REDIRECT_FIELD_NAME):
    from django.contrib.auth import logout
    logout(request)
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    return redirect(redirect_to or '/')
