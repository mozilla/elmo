# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Django template filters to be used to display compare-locales runs.
'''

from django import template
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from l10nstats.models import Run

register = template.Library()


@register.filter
def showrun(run):
    """Display a l10nstats.models.Run object in a template in a consistent
    manner.

    Since we're not accepting input strings we don't have to worry about
    autoescaping.
    """
    if not isinstance(run, Run):
        return mark_safe("&nbsp;")
    fmt = ('<a %%s href="%s?run=%%d">%%s</a>' %
            reverse('l10nstats.views.compare'))
    missing = run.missing + run.missingInFiles
    data = {'missing': missing}
    for k in ('errors', 'total'):
        data[k] = getattr(run, k)
    datastr = ' '.join('data-%s="%d"' % (k, v) for k, v in data.iteritems())
    cmp_segs = []
    if run.errors:
        cmp_segs.append('%d error(s)' % run.errors)
    if missing:
        cmp_segs.append('%d missing' % missing)
    if run.obsolete:
        cmp_segs.append('%d obsolete' % run.obsolete)
    if not cmp_segs:
        cmp_segs.append('green')
    cmp_segs.append('(%d%%)' % run.completion)
    compare = ', '.join(cmp_segs)

    return mark_safe(fmt % (datastr, run.id, compare))
