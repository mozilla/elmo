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

'''Django template filters to be used to display builds.
'''

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.core.urlresolvers import reverse

from mbdb.models import Change, Build, Step

register = template.Library()

@register.filter
def showbuild(build_or_step, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    if build_or_step is None:
        return mark_safe("&nbsp;")
    if isinstance(build_or_step, Change):
        # blame column
        c = build_or_step
        fmt = ('<a href="' + 
               reverse('tinder.views.builds_for_change')+ 
               '?change=%d" title="%s">%s</a>')
        return mark_safe(fmt % (c.number, c.when.isoformat(), esc(c.who)))
    if isinstance(build_or_step, Build):
        fmt = '<a href="%s" title="%s">Build %d</a><br/>%s %s'
        build = build_or_step
        b_url = reverse('tinder.views.showbuild',
                        args = [build.builder.name, build.buildnumber])
        rv = fmt % (b_url, build.starttime.isoformat(), build.buildnumber,
                    build.getProperty('tree'), build.getProperty('locale'))
        rv += '<br/>%s' % build.slave.name
        if build.sourcestamp.changes.count():
            fmt = ('<a href="' + 
                   reverse('tinder.views.builds_for_change')+ 
                   '?change=%d">%d</a>')
            links = map(lambda c: fmt % (c.number, c.number),
                        build.sourcestamp.changes.order_by('pk'))
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
        rows = map(lambda s: rowfmt % (res2class(s), showstep(s)),
                   build.steps.order_by('-pk'))
        body = ''.join(rows) + rowfmt % ('running', rv)
        return mark_safe(outer % body)
        
    return build_or_step.name
showbuild.needs_autoescape = True

@register.filter
def showstep(step, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x

    if step.starttime and step.endtime:
        step_t = step.endtime - step.starttime
        if step_t.days:
            # something funky, but wth
            step_t = "%d day(s)" % step_t.days
        else:
            step_t = step_t.seconds
            if step_t > 5*60:
                # we're longer than 5 mins, ignore seconds
                step_t = "%d minutes" % (step_t/60)
            elif step_t <= 90:
                step_t = "%d seconds" % step_t
            else:
                step_t = "%d minutes %d seconds" % (step_t/60, step_t%60)
    else:
        step_t = '-'
    class_ = res2class(step)
    fmt = '<span class="step_text">%s</span> <span class="step_time">%s</span>'
    result = fmt % (esc(' '.join(step.text)), step_t)
    return mark_safe(result)
showstep.needs_autoescape = True


@register.filter
def res2class(build_or_step):
    resultclasses = ['success', 'warning', 'failure', 'skip', 'except']
    try:
        class_ = resultclasses[build_or_step.result]
    except:
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
