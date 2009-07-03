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
