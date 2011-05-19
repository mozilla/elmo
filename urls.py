from django.conf.urls.defaults import *
from django.conf import settings
from django.http import HttpResponse
import base64
import re


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Example:
    # (r'^dashboard/', include('dashboard.foo.urls')),
                       (r'^privacy/', include('privacy.urls')),
                       (r'.*/__history__.html$', lambda r: HttpResponse()),
                       (r'^builds/',
                        include('tinder.urls')),
                       (r'^pushes/(?P<repo_name>.+)?$',
                        'pushes.views.pushlog', {}, 'pushlog'),
                       (r'^dashboard/', include('l10nstats.urls')),
                       (r'^shipping',
                            include('shipping.urls')),
                       (r'^bugs/',
                            include('bugsy.urls')),
                       (r'^webby/',
                            include('webby.urls')),
                       (r'^accounts/',
                            include('accounts.urls')),
                       (r'^',
                        include('homepage.urls')),
                       (r'^robots\.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: /*",
                                                                 mimetype="text/plain")),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

# Usually, you would include this only for DEBUG, but let's keep
# this so that we can reverse resolve static.
# That way, we can move the site to /stage/foo without messing with
# the references to /media/.

# Remove leading and trailing slashes so the regex matches.
media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
urlpatterns += patterns('',
    url(r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
     {'document_root': settings.MEDIA_ROOT},
     'static'),
)


# Proxy the webdashboard
urlpatterns += patterns('',
                        (r'^webdashboard/(?P<path>.*)$',
                         'l10nstats.views.proxy',
                         {'base': 'http://l10n.mozilla.org/webdashboard/'}, 'webdashboard'),
                        )
