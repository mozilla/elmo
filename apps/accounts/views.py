# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for logging in and out of l10n_site.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

import json
from django.http import HttpResponse
from django.views.decorators import cache


@cache.cache_control(private=True)
def user_json(request):
    result = {}
    if request.user.is_authenticated:
        if request.user.first_name:
            result['user_name'] = request.user.first_name
        else:
            result['user_name'] = request.user.username
    return HttpResponse(json.dumps(result), content_type="application/json")
