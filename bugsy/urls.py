from django.conf.urls.defaults import *

urlpatterns = patterns('bugsy.views',
    (r'^$', 'index'),
    (r'^new-locale$', 'new_locale'),
    (r'^new-locale-bugs.json$', 'new_locale_bugs'),
    (r'^file-bugs$', 'file_bugs'),
    (r'^bug-links$', 'get_bug_links'),
)
