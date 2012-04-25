# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for the bug handling pages.
'''

from django.http import HttpResponse
from django.template import Context, Template, RequestContext
from django.template.loader import render_to_string
from django.shortcuts import render
from django.utils import simplejson

from life.models import Locale


def index(request):
    return render(request, 'bugsy/index.html')


def homesnippet():
    return render_to_string('bugsy/snippet.html')


def teamsnippet(locale):
    bugs_url = ('https://bugzilla.mozilla.org/buglist.cgi?field0-0-0=component'
                 ';type0-0-0=regexp;value0-0-0=^%s / ;resolution=---'
                 % locale.code).replace(' ', '%20')
    return render_to_string('bugsy/team-snippet.html', {
                    'locale': locale,
                    'bugs_url': bugs_url,
                  })


def file_bugs(request):
    return render(request, 'bugsy/file-bugs.html')


def get_bug_links(request):
    locale_codes = request.GET.getlist('locales')
    locales = Locale.objects.filter(code__in=locale_codes)
    locale_names = dict(locales.values_list('code', 'name'))
    opts = dict((k, Template(v)) for k, v in request.GET.iteritems())
    opts.pop('locales')
    bugs = {}
    for loc in locale_codes:
        c = Context({
            'loc': loc,
            'locale': locale_names.get(loc, '[%s]' % loc),
        })
        item = dict((k, t.render(c)) for k, t in opts.iteritems())
        bugs[loc] = item
    return HttpResponse(simplejson.dumps(bugs, indent=2),
                        mimetype="application/json")


def new_locale(request):
    return render(request, 'bugsy/new-locale.html')


def new_locale_bugs(request):
    alias = request.GET.get('app', 'fx')
    return render(request, 'bugsy/new-%s-locales.json' % alias,
                  request.GET,
                  content_type='application/javascript')
