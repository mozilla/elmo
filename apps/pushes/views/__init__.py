# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from django.template.loader import render_to_string
from django.db.models import Max

from life.models import Repository

# make our view functions easy to reference as
# pushes.views.diff and .pushlog instead of .diff.diff
from .pushlog import pushlog
from .diff import diff
# make pyflakes happy
diff = diff
pushlog = pushlog
