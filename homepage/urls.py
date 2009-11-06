from django.conf.urls.defaults import *

urlpatterns = patterns('homepage.views',
                       (r'^$', 'index'),
                       (r'^teams/$', 'teams'),
                       (r'^teams/(.*)$', 'locale_team'),
                       )
