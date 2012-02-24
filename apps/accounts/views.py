# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

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
