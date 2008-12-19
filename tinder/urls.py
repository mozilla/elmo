from django.conf.urls.defaults import *

urlpatterns = patterns('tinder.views',
                       (r'^waterfall$', 'waterfall'),
                       (r'^builds_for', 'builds_for_change'),
                       (r'^builders/([^/]+)/(\d+)', 'showbuild'),
                       )
