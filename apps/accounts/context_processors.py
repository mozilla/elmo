# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from .forms import AuthenticationForm
from django.conf import settings


def accounts(request):
    ctx = {
        'OIDC_DISABLE': settings.OIDC_DISABLE
    }
    if settings.OIDC_DISABLE:
        login_form = AuthenticationForm()
        ctx['login_form'] = login_form
    return ctx
