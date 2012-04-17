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

'''Views for the bug handling pages.
'''

from django.http import HttpResponse
from django.template import Context, Template
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
