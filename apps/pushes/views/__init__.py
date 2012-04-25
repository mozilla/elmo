# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from django.template.loader import render_to_string
from django.db.models import Max

from life.models import Repository

# make our view functions easy to reference as
# pushes.views.diff and .pushlog instead of .diff.diff
from pushlog import pushlog
from diff import diff
# make pyflakes happy
diff = diff
pushlog = pushlog


def homesnippet():
    repos = Repository.objects.filter(forest__isnull=False)
    repos = repos.annotate(lpd=Max('push__push_date'))
    repos = repos.order_by('-lpd')
    return render_to_string('pushes/snippet.html', {
            'repos': repos[:5],
            })
