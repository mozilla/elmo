# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for compare-locales output and statistics, in particular dashboards
and progress graphs.
'''
from __future__ import absolute_import, division
from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpResponsePermanentRedirect

from l10nstats.models import Run
import shipping.views


def index(request):
    """redirect to the new improved dashboard which had all the features of the
    l10nstats dashboard.
    """
    url = reverse(shipping.views.dashboard)
    if request.META.get('QUERY_STRING'):
        url += '?' + request.META.get('QUERY_STRING')
    return HttpResponsePermanentRedirect(url)


def teamsnippet(loc):
    act = Run.objects.filter(locale=loc, active__isnull=False)
    week_ago = datetime.utcnow() - timedelta(7)
    act = act.filter(srctime__gt=week_ago)
    act = act.order_by('tree__code').select_related('tree')
    return render_to_string('l10nstats/team-snippet.html', {
            'actives': act,
            })
