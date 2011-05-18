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
