# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Template tags to include locally hosted Simile widgets into dashboards.
'''

from django import template
from django.core.urlresolvers import reverse


register = template.Library()


def simile(parser, token, apps, forceBundle=False):
    """Generic function for simile api inclusions
    """

    args = token.split_contents()[1:]
    simileurl = reverse('static', kwargs={'path': 'simile/'})
    opts = {'bundle': 'true', 'autoCreate': 'true'}
    for arg in args:
        try:
            k, v = arg.split('=', 1)
            if k in opts:
                opts[k] = v
        except ValueError:
            pass
    bundle = opts['bundle'] == 'false' and 'bundle=false' or None
    if bundle is None and forceBundle:
        bundle = 'bundle=true'
    autoCreate = opts['autoCreate'] == 'false' and 'autoCreate=false' or None
    ajax_params = '&'.join(filter(None, [bundle]))
    if ajax_params:
        ajax_params = '?' + ajax_params
    app_params = '&'.join(filter(None, [bundle, autoCreate]))
    if app_params:
        app_params = '?' + app_params
    script_head = '''<script type="text/javascript">
(function() {
  '''
    script_tail = '''
})();
</script>
<script type="text/javascript" '''\
'''src="%(base)sajax/simile-ajax-api.js%(params)s"></script>
''' % {'base': simileurl, 'params': ajax_params}
    loaders = []
    next = None
    params = app_params
    for app in reversed(apps):
        loaders += ['function load_%s() {' % app]
        if next is not None:
            loaders += ['  window.SimileAjax_onLoad = load_%s;' % next]
        loaders += [
            '  SimileAjax.includeJavascriptFile(document, "%(base)s%(app)s/'\
            '%(app)s-api.js%(params)s");' % \
            {'base': simileurl, 'app': app, 'params': params},
            '};']
        next = app
        params = ajax_params
    loaders += ['window.SimileAjax_onLoad = load_%s;' % next]
    out = (script_head + '\n  '.join(loaders) + script_tail)
    return template.TextNode(out)


@register.tag
def exhibit(parser, token):
    """Add simile exhibit to the page.
    """
    return simile(parser, token, ('exhibit',))


@register.tag
def timeplot(parser, token):
    """Add simile timeplot to the page.

    Includes timeline.
    """
    return simile(parser, token, ('timeline', 'timeplot'), forceBundle=True)
