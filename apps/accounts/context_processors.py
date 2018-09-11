# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from .forms import AuthenticationForm


def accounts(request):
    login_form = AuthenticationForm()
    return {'login_form': login_form}
