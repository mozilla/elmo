# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for the bug handling pages.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.http import HttpResponse
from django.template import Context, Template
from django.shortcuts import render
import json
import six

from life.models import Locale


def index(request):
    return render(request, 'bugsy/index.html')


def teamsnippet(locale):
    bugs_url = (
        'https://bugzilla.mozilla.org/buglist.cgi?'
        'j_top=OR&'
        '&o1=regexp&v1=^%s / &f1=component'
        '&o2=regexp&v2=^%s / &f2=cf_locale'
        '&resolution=---'
        % (locale.code, locale.code)
    ).replace(' ', '%20')
    return {
        'template': 'bugsy/team-snippet.html',
        'context': {
            'locale': locale,
            'bugs_url': bugs_url,
        }
    }


def file_bugs(request):
    return render(request, 'bugsy/file-bugs.html')


def get_bug_links(request):
    locale_codes = request.GET.getlist('locales')
    locales = Locale.objects.filter(code__in=locale_codes)
    locale_names = dict(locales.values_list('code', 'name'))
    opts = {k: Template(v) for k, v in six.iteritems(request.GET)}
    opts.pop('locales')
    bugs = {}
    for loc in locale_codes:
        c = Context({
            'loc': loc,
            'locale': locale_names.get(loc, '[%s]' % loc),
        })
        item = {k: t.render(c) for k, t in six.iteritems(opts)}
        bugs[loc] = item
    return HttpResponse(json.dumps(bugs, indent=2),
                        content_type="application/json")


def new_locale(request):
    return render(request, 'bugsy/new-locale.html')


def new_locale_bugs(request):
    alias = request.GET.get('app', 'fx')
    return render(request, 'bugsy/new-%s-locales.json' % alias,
                  request.GET.dict(),
                  content_type='application/javascript')
