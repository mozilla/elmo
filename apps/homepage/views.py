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

'''Views for the main navigation pages.
'''

import sys
import feedparser  # vendor-local
from django.core.urlresolvers import reverse
from django.http import (HttpResponsePermanentRedirect, Http404,
                         HttpResponseServerError)
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from django.template import RequestContext, loader
from django.conf import settings
from django.shortcuts import render
from django.views.defaults import page_not_found, server_error
from django.core.cache import cache
import django_arecibo.wrapper

from life.models import Locale


def handler404(request):
    if getattr(settings, 'ARECIBO_SERVER_URL', None):
        # Make a distinction between Http404 and Resolver404.
        # Http404 is an explicity exception raised from within the views which
        # might indicate the wrong usage of arguments to a view for example.
        # Resolver404 is an implicit exception that Django raises when it can't
        # resolve a URL to an appropriate view or handler.
        # We're not interested in sending Arecibo exceptions on URLs like
        # /blablalb/junk/junk
        # but we might be interested in /dashboard?from=20LL-02-31
        exception = sys.exc_info()[0]
        if isinstance(exception, Http404) or exception is Http404:
            django_arecibo.wrapper.post(request, 404)
    return page_not_found(request)


def handler500(request):
    if getattr(settings, 'ARECIBO_SERVER_URL', None):
        django_arecibo.wrapper.post(request, 500)
    # unlike the default django.views.default.server_error view function we
    # want one that passes a RequestContext so that we can have 500.html
    # template that uses '{% extends "base.html" %}' which depends on various
    # context variables to be set
    t = loader.get_template('500.html')
    return HttpResponseServerError(t.render(RequestContext(request)))


def index(request):
    split = 6
    locales = Locale.objects.filter(name__isnull=False).order_by('name')

    feed_items = get_feed_items()

    options = {
      'feed_items': feed_items,
      'locales_first_half': locales[:split],
      'locales_second_half': locales[split:split * 2 - 1],
      'locales_rest_count': locales.count() - split * 2 - 1,
    }
    return render(request, 'homepage/index.html', options)


def get_feed_items(max_count=settings.HOMEPAGE_FEED_SIZE,
                   force_refresh=False):
    cache_key = 'feed_items:%s' % max_count
    if not force_refresh:
        items = cache.get(cache_key, None)
        if items is not None:
            return items

    parsed = feedparser.parse(settings.L10N_FEED_URL)

    items = []
    for item in parsed.entries:
        url = item['link']
        title = item['title']
        if url and title:
            items.append(dict(url=url, title=title))
            if len(items) >= max_count:
                break

    cache.set(cache_key, items, 60 * 60)
    return items


def teams(request):
    locs = Locale.objects.all().order_by('name')
    # This is an artifact of the addon trees
    # see https://bugzilla.mozilla.org/show_bug.cgi?id=701218
    locs = locs.exclude(code='en-US')
    return render(request, 'homepage/teams.html', {
                    'locales': locs,
                  })


def locale_team(request, code):
    try:
        loc = Locale.objects.get(code=code)
    except Locale.DoesNotExist:
        return redirect('homepage.views.teams')

    from l10nstats.views import teamsnippet as stats_snippet
    l10nstats_div = mark_safe(stats_snippet(loc))

    from shipping.views import teamsnippet as ship_snippet
    ship_div = mark_safe(ship_snippet(loc))

    from bugsy.views import teamsnippet as bug_snippet
    bug_div = mark_safe(bug_snippet(loc))

    name = loc.name or loc.code

    return render(request, 'homepage/locale-team.html', {
                    'locale': loc,
                    'locale_name': name,
                    'l10nstats': l10nstats_div,
                    'shipping': ship_div,
                    'bugs': bug_div,
                  })

# redirects for moves within pushes app, and moving the diff view
# from shipping to pushes.
# XXX Revisit how long we need to keep those


def pushlog_redirect(request, path):
    return HttpResponsePermanentRedirect(
        reverse('pushes.views.pushlog.pushlog',
                kwargs={'repo_name': path}) + '?' + request.GET.urlencode())


def diff_redirect(request):
    return HttpResponsePermanentRedirect(
        reverse('pushes.views.diff') + '?' + request.GET.urlencode())
