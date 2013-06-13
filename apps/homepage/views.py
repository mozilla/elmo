# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views for the main navigation pages.
'''

import datetime
import sys
import feedparser  # vendor-local
from django.core.urlresolvers import reverse
from django.http import (HttpResponsePermanentRedirect, Http404,
                         HttpResponseServerError)
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from django.template import RequestContext, loader
from django.conf import settings
from django.views.defaults import page_not_found
from django.core.cache import cache
from django.views.decorators.http import etag

from life.models import Locale


def handler500(request):
    # unlike the default django.views.default.server_error view function we
    # want one that passes a RequestContext so that we can have 500.html
    # template that uses '{% extends "base.html" %}' which depends on various
    # context variables to be set
    t = loader.get_template('500.html')
    return HttpResponseServerError(t.render(RequestContext(request)))


def etag_index(request):
    cache_key = 'homepage.views.index.etag'
    tag = cache.get(cache_key)
    if tag is None:
        # because the Locale model doesn't have a modify time thing, we can
        # just any unique value to this moment.
        tag = datetime.datetime.now().strftime('%f')  # microseconds

        # the home page depends on the cache for the feed
        # 1 hour is the same as a expiration time for the L10n feed
        cache.set(cache_key, tag, 60 * 60)
    return tag


@etag(etag_index)
def index(request):
    limit = getattr(settings, 'HOMEPAGE_LOCALES_LIMIT', 10)

    locales_first_half, locales_second_half, locales_rest_count = \
      get_homepage_locales(limit / 2)

    feed_items = get_feed_items()

    locs = Locale.objects.all().order_by('name')
    locs = locs.exclude(code='en-US')

    options = {
      'locales': locs,
      'feed_items': feed_items,
      'locales_first_half': locales_first_half,
      'locales_second_half': locales_second_half,
      'locales_rest_count': locales_rest_count,
    }
    return render(request, 'homepage/index.html', options)


def get_homepage_locales(split):
    # we're only going to show the `split+split-1` first locales
    # and in the interest to avoid excessive db queries, download
    # them all as a python list and split up accordingly
    locales = list(Locale.objects
                   .filter(name__isnull=False)
                   .order_by('name')
                   .values('name', 'code'))
    length = len(locales)
    if split * 2 > length:
        split = length / 2  # new minimum split
    first_half = locales[:split]
    second_half = locales[split:split * 2 - 1]
    rest_count = length - split * 2 + 1
    return first_half, second_half, rest_count


def get_feed_items(max_count=settings.HOMEPAGE_FEED_SIZE,
                   force_refresh=False):
    cache_key = 'feed_items:%s' % max_count
    if not force_refresh:
        items = cache.get(cache_key, None)
        if items is not None:
            return items

    # if we have to re-parse the feed, then lets also invalidate the homepage
    # etag.
    if force_refresh:
        cache.delete('homepage.views.index.etag')

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

    from shipping.views import teamsnippet as ship_snippet
    ship_div = mark_safe(ship_snippet(loc))

    from bugsy.views import teamsnippet as bug_snippet
    bug_div = mark_safe(bug_snippet(loc))

    name = loc.name or loc.code

    gliblocale = settings.VERBATIM_CONVERSIONS.get(
        loc.code,
        loc.code.replace('-', '_')
    )
    if gliblocale:
        verbatim_url = 'https://localize.mozilla.org/%s/' % gliblocale
    else:
        verbatim_url = None

    return render(request, 'homepage/locale-team.html', {
                    'locale': loc,
                    'locale_name': name,
                    'shipping': ship_div,
                    'bugs': bug_div,
                    'webdashboard_url': settings.WEBDASHBOARD_URL,
                    'verbatim_url': verbatim_url,
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
