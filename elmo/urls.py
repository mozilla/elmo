# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView
from session_csrf import anonymous_csrf


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
    url(r'^__version__$',
        TemplateView.as_view(template_name='version.json',
                             content_type='application/json')),

    url(
        r'^login/$',
        anonymous_csrf(auth_views.LoginView.as_view()),
        name='login'
    ),
    url(r'^logout/$', auth_views.LogoutView.as_view(), name='logout'),

    url(r'^admin/', admin.site.urls),
]


handler500 = 'homepage.views.handler500'

if 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
