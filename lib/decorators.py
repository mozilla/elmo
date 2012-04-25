# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django import http


def require_post(f):
    def wrapper(request, *args, **kw):
        if request.method == 'POST':
            return f(request, *args, **kw)
        else:
            return http.HttpResponseNotAllowed(['POST'])
    return wrapper
