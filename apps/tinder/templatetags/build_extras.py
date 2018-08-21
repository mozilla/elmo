# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Django template filters to be used to display builds.
'''
from __future__ import absolute_import, division
from __future__ import unicode_literals

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.core.urlresolvers import reverse

from mbdb.models import Change, Build
import tinder.views

register = template.Library()


@register.filter
def showbuild(build_or_step, autoescape=None):
    def esc(input):
        if autoescape:
            return conditional_escape(input)
        return input
    if build_or_step is None:
        return mark_safe("&nbsp;")
    if isinstance(build_or_step, Change):
        # blame column
        change = build_or_step
        fmt = ('<a href="' +
               reverse(tinder.views.builds_for_change) +
               '?change=%d" title="%s">%s</a>')
        return mark_safe(
            fmt % (change.number, change.when.isoformat(), esc(change.who))
        )
    if isinstance(build_or_step, Build):
        fmt = '<a href="%s" title="%s">Build %d</a><br/>%s %s'
        build = build_or_step
        b_url = reverse('tinder-showbuild',
                        args=[build.builder.name, build.buildnumber])
        rv = fmt % (b_url, build.starttime.isoformat(), build.buildnumber,
                    build.getProperty('tree'), build.getProperty('locale'))
        rv += '<br/>%s' % build.slave.name
        if build.sourcestamp.changes.count():
            fmt = ('<a href="' +
                   reverse(tinder.views.builds_for_change) +
                   '?change=%d">%d</a>')
            links = [
                fmt % (c.number, c.number)
                for c in build.sourcestamp.changes.order_by('pk')
            ]
            rv += '<br/>Changes ' + ', '.join(links)
        if build.endtime is not None:
            # We're a finished build, just show the build
            return mark_safe(rv)
        outer = '''<table class="builddetails" border="1" cellspacing="0">
%s
</table>
'''
        rowfmt = '''<tr><td class="%s">%s</td></tr>
'''
        rows = [
            rowfmt % (res2class(s), showstep(s))
            for s in build.steps.order_by('-pk')
        ]
        body = ''.join(rows) + rowfmt % ('running', rv)
        return mark_safe(outer % body)
    return build_or_step.name
showbuild.needs_autoescape = True  # noqa


@register.filter
def showstep(step, autoescape=None):
    def esc(input):
        if autoescape:
            return conditional_escape(input)
        return input

    if step.starttime and step.endtime:
        step_t = step.endtime - step.starttime
        if step_t.days:
            # something funky, but wth
            step_t = "%d day(s)" % step_t.days
        else:
            step_t = step_t.seconds
            if step_t > 5 * 60:
                # we're longer than 5 mins, ignore seconds
                step_t = "%d minutes" % (step_t // 60)
            elif step_t <= 90:
                step_t = "%d seconds" % step_t
            else:
                step_t = "%d minutes %d seconds" % (step_t // 60, step_t % 60)
    else:
        step_t = '-'
    fmt = '<span class="step_text">%s</span> <span class="step_time">%s</span>'
    result = fmt % (esc(' '.join(step.text)), step_t)
    return mark_safe(result)
showstep.needs_autoescape = True  # noqa


@register.filter
def res2class(build_or_step):
    resultclasses = ['success', 'warning', 'failure', 'skip', 'except']
    try:
        class_ = resultclasses[build_or_step.result]
    except (TypeError, IndexError):
        if build_or_step.starttime:
            class_ = 'running'
        else:
            class_ = ''
    return mark_safe(class_)


@register.filter
def timedelta(start, end):
    if start is None or end is None:
        return mark_safe('-')
    td = end - start
    rv = []
    if td.days:
        rv.append('%d day(s)' % td.days)
    minutes, seconds = divmod(td.seconds, 60)
    if minutes:
        rv.append('%d minute(s)' % minutes)
    if seconds:
        rv.append('%d second(s)' % seconds)

    return ' '.join(rv)
