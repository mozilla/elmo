from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^dashboard/', include('dashboard.foo.urls')),
                       (r'^builds/',
                        include('tinder.urls')),
                       (r'^pushes/(?:(?P<repo_name>.*)/)?$',
                        'pushes.views.pushlog', {}, 'pushlog'),
                       (r'^status/l10n-repos$',
                        'status.views.repostatus'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
)

# Usually, you would include this only for DEBUG, but let's keep
# this so that we can reverse resolve static.
# That way, we can move the site to /stage/foo without messing with
# the references to /static/.
urlpatterns += patterns('',
                        (r'^static/(?P<path>.*)$',
                         'django.views.static.serve',
                         {'document_root': 'static/'}, 'static'),
                        )
