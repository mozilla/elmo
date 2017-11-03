# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.conf import settings
from django.http import HttpResponse
import django.views.static
from django.views.generic import TemplateView

## Monkeypatches:
## ... don't go here anymore, but in to elmo.apps.ElmoConfig

def simple_x_frame_view(request):
    response = HttpResponse()
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response


urlpatterns = [
    url(r'^privacy/', include('privacy.urls', namespace='privacy')),
    url(r'.*/__history__.html$', simple_x_frame_view),
    url(r'^builds/', include('tinder.urls')),
    url(r'^source/', include('pushes.urls', namespace='pushes')),
    url(r'^dashboard/', include('l10nstats.urls')),
    url(r'^shipping/', include('shipping.urls')),
    url(r'^bugs/', include('bugsy.urls')),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^', include('homepage.urls')),
    url(r'^contribute.json$',
        TemplateView.as_view(template_name='contribute.json',
                             content_type='application/json')),
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', admin.site.urls),
]


handler500 = 'homepage.views.handler500'

# Usually, you would include this only for DEBUG, but let's keep
# this so that we can reverse resolve static.
# That way, we can move the site to /stage/foo without messing with
# the references to /media/.

# Remove leading and trailing slashes so the regex matches.
# TODO: consider subclassing django.views.static.serve with something
# that prints a warning message
static_url = settings.STATIC_URL.lstrip('/').rstrip('/')
urlpatterns += [
    url(r'^%s/(?P<path>.*)$' % static_url, django.views.static.serve,
     {'document_root': settings.STATIC_ROOT},
     'static'),
]

#if settings.DEBUG:
urlpatterns += staticfiles_urlpatterns()

if 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
