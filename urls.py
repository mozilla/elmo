# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import include, patterns, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.http import HttpResponse

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

## Monkeypatches:
## Here's the ideal place to put them if you need to monkeypatches anything
## during Django's start-up.
## ...


def simple_x_frame_view(request):
    response = HttpResponse()
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response


urlpatterns = patterns('',
    # Example:
    # (r'^dashboard/', include('dashboard.foo.urls')),
                       (r'^privacy/', include('privacy.urls')),
                       (r'.*/__history__.html$', simple_x_frame_view),
                       (r'^builds/', include('tinder.urls')),
                       (r'^source/', include('pushes.urls')),
                       (r'^dashboard/', include('l10nstats.urls')),
                       (r'^shipping', include('shipping.urls')),
                       (r'^bugs/', include('bugsy.urls')),
                       (r'^accounts/', include('accounts.urls')),
                       (r'^', include('homepage.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)


handler500 = 'homepage.views.handler500'

# Usually, you would include this only for DEBUG, but let's keep
# this so that we can reverse resolve static.
# That way, we can move the site to /stage/foo without messing with
# the references to /media/.

# Remove leading and trailing slashes so the regex matches.
# TODO: consider subclassing django.views.static.serve with something
# that prints a warning message
static_url = settings.STATIC_URL.lstrip('/').rstrip('/')
urlpatterns += patterns('',
    url(r'^%s/(?P<path>.*)$' % static_url, 'django.views.static.serve',
     {'document_root': settings.STATIC_ROOT},
     'static'),
)

#if settings.DEBUG:
urlpatterns += staticfiles_urlpatterns()
