'''Views for the bug handling pages.
'''

from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.utils.safestring import mark_safe
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils import simplejson

import re

from bugsy.models import *


def index(request):
    return render_to_response('bugsy/index.html', {
            })


def homesnippet(request):
    return render_to_string('bugsy/snippet.html', {})

def teamsnippet(request, locale):
    return render_to_string('bugsy/team-snippet.html', {'locale': locale})


def file_bugs(request):
    return render_to_response('bugsy/file-bugs.html', {
            })

def get_bug_links(request):
    locales = request.GET.getlist('locales')
    opts = dict((k, Template(v)) for k, v in request.GET.iteritems())
    opts.pop('locales')
    bugs = {}
    for loc in locales:
        c = Context({'loc': loc})
        item = dict((k, t.render(c)) for k, t in opts.iteritems())
        bugs[loc] = item
    return HttpResponse(simplejson.dumps(bugs, indent=2),
                        mimetype="application/json")


def new_locale(request):
    return render_to_response('bugsy/new-locale.html')


def new_locale_bugs(request):
    return render_to_response('bugsy/new-locales.json',
                              request.GET,
                              mimetype="application/javascript")
