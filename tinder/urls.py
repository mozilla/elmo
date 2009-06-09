from django.conf.urls.defaults import *
from views import BuildsForChangeFeed

feeds = {
    'builds_for_change': BuildsForChangeFeed,
    }

urlpatterns = patterns('tinder.views',
                       (r'^waterfall$', 'waterfall'),
                       (r'^builds_for', 'builds_for_change'),
                       (r'^builders/([^/]+)/(\d+)', 'showbuild',
                        {}, 'tinder_show_build'),
                       (r'^log/([^/]+)/(.+)', 'showlog', {}, 'showlog'),
                       (r'^feeds/(?P<url>.*)/$', 'feed',
                        {'feed_dict': feeds}),
                       )
